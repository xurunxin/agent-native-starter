"""Read-only API contracts; unsupported writes fail without sending a request."""
from dataclasses import dataclass
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener


class ProviderError(RuntimeError):
    def __init__(self, code, status=None):
        self.code, self.status = code, status
        super().__init__(f'{code}' + (f' (HTTP {status})' if status else ''))


@dataclass
class Response:
    status: int
    data: object
    headers: dict


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_get(url, headers):
    """No redirects: never forward authorization to a new host."""
    try:
        with build_opener(NoRedirect()).open(Request(url, headers=headers), timeout=20) as r:
            return Response(r.status, json.load(r), dict(r.headers))
    except HTTPError as e:
        return Response(e.code, None, dict(e.headers))
    except (URLError, OSError, ValueError):
        raise ProviderError('transport_error') from None


class Provider:
    READS = ('issues', 'issue', 'pull_requests', 'pull_request', 'comments',
             'statuses', 'branches', 'branch', 'checks', 'protection', 'repository')
    WRITES = ('create_issue', 'create_pull_request', 'comment', 'set_status',
              'create_branch', 'set_protection')

    def __init__(self, kind, api_url, repository, *, token=None, trusted=True,
                 transport=http_get, sleep=time.sleep, attempts=3, max_pages=100):
        parsed = urlsplit(api_url)
        if kind not in ('github', 'gitea') or parsed.scheme != 'https' or not parsed.netloc:
            raise ValueError('Choose github/gitea and an HTTPS API URL')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('API URL cannot contain credentials, query or fragment')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Expected owner/repository')
        if any(part in ('.', '..') for part in repository.split('/')):
            raise ValueError('Invalid repository segment')
        if token and not trusted:
            raise ValueError('Credentials are prohibited in untrusted execution')
        if not 1 <= attempts <= 5 or not 1 <= max_pages <= 1000:
            raise ValueError('Retry/page budgets out of bounds')
        self.kind, self.api_url = kind, api_url.rstrip('/')
        self.root = self.api_url + '/repos/' + repository
        self.transport, self.sleep = transport, sleep
        self.attempts, self.max_pages = attempts, max_pages
        self.headers = {'Accept': 'application/json'}
        if token:
            self.headers['Authorization'] = ('Bearer ' if kind == 'github' else 'token ') + token

    def _get(self, url):
        if urlsplit(url).netloc != urlsplit(self.api_url).netloc or urlsplit(url).scheme != 'https':
            raise ProviderError('unsafe_pagination')
        for attempt in range(self.attempts):
            try:
                r = self.transport(url, self.headers.copy())
            except Exception:
                if attempt + 1 == self.attempts:
                    raise ProviderError('transport_error') from None
                self.sleep(2 ** attempt)
                continue
            r.headers = {k.lower(): v for k, v in r.headers.items()}
            limited = r.status == 429 or (r.status == 403 and (
                r.headers.get('x-ratelimit-remaining') == '0' or 'retry-after' in r.headers))
            transient = r.status in (500, 502, 503, 504)
            if limited or transient:
                if attempt + 1 < self.attempts:
                    try:
                        delay = float(r.headers.get('retry-after', 2 ** attempt))
                    except (ValueError, TypeError):
                        delay = 2 ** attempt
                    # Do not retry before a long server-requested delay.
                    if delay > 60 or delay < 0:
                        raise ProviderError('rate_limited' if limited else 'server_error', r.status)
                    self.sleep(delay)
                    continue
                raise ProviderError('rate_limited' if limited else 'server_error', r.status)
            if r.status >= 400 or 300 <= r.status < 400:
                code = {401: 'unauthorized', 403: 'forbidden', 404: 'not_found',
                        409: 'conflict', 422: 'invalid_request'}.get(r.status, 'http_error')
                raise ProviderError(code, r.status)
            return r

    def _list(self, path, *, items_key=None, **query):
        query['per_page' if self.kind == 'github' else 'limit'] = 100
        start = self.root + path
        url = start + '?' + urlencode(query)
        seen, result = set(), []
        for page in range(1, self.max_pages + 1):
            if url in seen:
                raise ProviderError('pagination_cycle')
            seen.add(url)
            r = self._get(url)
            if items_key:
                r.data = r.data.get(items_key) if isinstance(r.data, dict) else None
            if not isinstance(r.data, list) or any(not isinstance(x, dict) for x in r.data):
                raise ProviderError('invalid_response')
            result.extend(r.data)
            links = re.findall(r'<([^>]+)>;\s*rel="next"', r.headers.get('link', ''))
            if links:
                url = urljoin(url, links[0])
            elif self.kind == 'gitea' and 'x-pagecount' in r.headers:
                try:
                    count = int(r.headers['x-pagecount'])
                except ValueError:
                    raise ProviderError('invalid_response') from None
                if page >= count:
                    return result
                url = start + '?' + urlencode({**query, 'page': page + 1})
            else:
                return result
        raise ProviderError('pagination_budget_exhausted')

    def repository(self):
        return self._get(self.root).data

    def issues(self, state='open'):
        return [x for x in self._list('/issues', state=state) if 'pull_request' not in x]

    def issue(self, number):
        return self._get(self.root + '/issues/' + quote(str(number), safe='')).data

    def pull_requests(self, state='open'):
        return self._list('/pulls', state=state)

    def pull_request(self, number):
        return self._get(self.root + '/pulls/' + quote(str(number), safe='')).data

    def comments(self, number):
        return self._list('/issues/' + quote(str(number), safe='') + '/comments')

    def statuses(self, sha):
        sha = quote(sha, safe='')
        # Commit statuses only; GitHub Checks API is a distinct unsupported contract.
        if self.kind == 'github':
            return self._list('/commits/' + sha + '/statuses')
        return self._list('/statuses/' + sha)

    def branch(self, name):
        return self._get(self.root + '/branches/' + quote(name, safe='')).data

    def branches(self):
        return self._list('/branches')

    def checks(self, sha):
        if self.kind != 'github':
            raise ProviderError('not_implemented')
        return self._list('/commits/' + quote(sha, safe='') + '/check-runs', items_key='check_runs')

    def protection(self, name):
        name = quote(name, safe='')
        path = '/branches/' + name + '/protection' if self.kind == 'github' else '/branch_protections/' + name
        return self._get(self.root + path).data

    def capability(self, feature):
        """Observed read access only. Never infers write authority from read success."""
        probes = {'issues': lambda: self.issues(), 'pull_requests': lambda: self.pull_requests(),
                  'repository': self.repository,
                  'protection': lambda: self.protection(self.repository()['default_branch'])}
        if feature not in probes:
            return 'not_implemented'
        try:
            probes[feature]()
            return 'supported'
        except ProviderError as e:
            if e.code in ('forbidden', 'unauthorized'):
                return 'denied'
            return 'unknown'

    def mutate(self, operation, payload):
        """No mutation adapter yet, including idempotent writes. No network side effects."""
        raise ProviderError('not_implemented')
