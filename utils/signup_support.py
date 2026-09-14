"""Explicitly configured, phone-scoped staging signup adapters.

No endpoint defaults and no production account reset. Snapshot a restoration token
before preparation; callers must restore even when preparation or a test fails.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoStagingRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward phone payloads or bearer tokens to a redirect.


class SignupPrerequisiteMissing(RuntimeError):
    pass


def state_api_configured(data):
    config = data.get('staging_api', {})
    return bool(config.get('base_url') and all(config.get(key) for key in ('snapshot', 'prepare', 'restore')))


def leaf_values(value):
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in leaf_values(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in leaf_values(item)]
    return [value]


class SignupStagingClient:
    def __init__(self, data, operations):
        self.mobile = data['mobile_number']
        self.config = data.get('staging_api', {})
        if os.getenv('SIGNUP_STAGING_API_APPROVED', 'false').lower() != 'true':
            raise SignupPrerequisiteMissing('Set SIGNUP_STAGING_API_APPROVED=true only for an approved staging API')
        base = self.config.get('base_url')
        if not base:
            raise SignupPrerequisiteMissing('Configure staging_api.base_url and verified endpoint schemas in signup_data.json')
        parsed = urlsplit(base)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Staging base URL must not contain credentials, query or fragment')
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')):
            raise ValueError('Use HTTPS for staging APIs; HTTP is allowed only on loopback')
        self.base = base.rstrip('/') + '/'
        self.opener = build_opener(NoStagingRedirects())
        self.operations = operations
        for name in operations:
            endpoint = self.config.get(name)
            if not isinstance(endpoint, dict) or not endpoint.get('path') or not endpoint.get('method'):
                raise SignupPrerequisiteMissing(f'Configure verified staging_api.{name}.method/path')
            method = endpoint['method'].upper()
            if method != ('GET' if name in ('snapshot', 'probe') else 'POST'):
                raise ValueError(f'{name}: GET is required for read-only operations; POST for prepare/restore')
            path = endpoint['path']
            if urlsplit(path).scheme or urlsplit(path).netloc or path.startswith('//'):
                raise ValueError('Endpoint paths must remain on the configured staging origin')
            if '..' in unquote(urlsplit(path).path).split('/'):
                raise ValueError('Staging endpoint path traversal is not allowed')
            if name in ('snapshot', 'probe'):
                if '{mobile_number}' not in path:
                    raise ValueError('Read-only endpoint path/query must explicitly scope mobile_number')
            else:
                payload = endpoint.get('payload')
                if not isinstance(payload, dict) or '{mobile_number}' not in leaf_values(payload):
                    raise ValueError('Prepare/restore payload must explicitly scope mobile_number')
                if name == 'restore' and '{restore_token}' not in leaf_values(payload):
                    raise ValueError('Restore payload must use the captured restore_token')

    def _render(self, value, variables):
        if isinstance(value, dict):
            return {key: self._render(item, variables) for key, item in value.items()}
        if isinstance(value, list):
            return [self._render(item, variables) for item in value]
        if isinstance(value, str):
            return value.format_map(variables)
        return value

    def call(self, operation, sup_id='', restore_token=''):
        if operation not in self.operations:
            raise ValueError('Operation was not validated/approved for this adapter')
        endpoint = self.config[operation]
        variables = {'mobile_number': self.mobile, 'sup_id': sup_id, 'restore_token': restore_token}
        path = self._render(endpoint['path'], {key: quote(str(value), safe='') for key, value in variables.items()})
        target = urljoin(self.base, path)
        if urlsplit(target).netloc != urlsplit(self.base).netloc or urlsplit(target).scheme != urlsplit(self.base).scheme:
            raise ValueError('Refusing a staging origin change')
        payload = None
        headers = {'Accept': 'application/json'}
        if endpoint['method'].upper() == 'POST':
            body = self._render(endpoint['payload'], variables)
            if self.mobile not in leaf_values(body):
                raise ValueError('Refusing a write payload without the exact requested phone value')
            payload = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        token = os.getenv('SIGNUP_STAGING_TOKEN')
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = Request(target, data=payload, headers=headers, method=endpoint['method'].upper())
        try:
            with self.opener.open(request, timeout=15) as response:
                result = json.load(response)
        except HTTPError as error:
            raise RuntimeError(f'Staging signup {operation} failed with HTTP {error.code}; response omitted to protect account/token data') from None
        except URLError:
            raise RuntimeError(f'Staging signup {operation} could not connect; check the approved API configuration') from None
        if not isinstance(result, dict):
            raise ValueError('Staging adapter requires a JSON object response')
        mobile_key = self.config.get('mobile_response_key', 'mobile_number')
        if str(result.get(mobile_key, '')) != self.mobile:
            raise ValueError('Staging response did not confirm the requested phone scope')
        return result

    def snapshot(self):
        result = self.call('snapshot')
        key = self.config.get('restore_token_response_key', 'restore_token')
        token = result.get(key)
        if not isinstance(token, str) or not token:
            raise ValueError('Snapshot must return a nonempty restoration token BEFORE any account preparation')
        return token

    def prepare(self, sup_id):
        return self.call('prepare', sup_id=sup_id)

    def restore(self, token):
        return self.call('restore', restore_token=token)

    def probe(self):
        return self.call('probe')
