"""Kontrollerede fejlmetadata fra Cloudflare. Ingen rå prompts eller credentials."""
import json
import re


class BilledAPIError(ValueError):
    def __init__(self, status, payload):
        errors = payload.get('errors', []) if isinstance(payload, dict) else []
        codes, messages = [], []
        for error in errors if isinstance(errors, list) else []:
            if not isinstance(error, dict):
                continue
            code = error.get('code')
            if type(code) is int:
                codes.append(code)
            if isinstance(error.get('message'),str):
                messages.append(error['message'].lower())
        text = ' '.join(messages)
        category = 'ukendt'
        for name, pattern in [
            ('promptlaengde', r'(prompt|input|sequence).*(too long|length|maximum|max length|token limit)'),
            ('billedstoerrelse', r'(width|height|dimension|resolution)'),
            ('multipart', r'(multipart|content.type|boundary)'),
            ('kvote', r'(quota|credit|billing|neurons|daily limit)'),
            ('adgang', r'(unauthorized|permission|authentication|invalid token)'),
            ('sikkerhedsfilter', r'(safety|moderation|nsfw|content filter)'),
            ('kapacitet', r'(capacity|queue|busy|temporarily unavailable)')]:
            if re.search(pattern,text):
                category = name
                break
        self.details = {'http_status': status, 'koder': codes[:5], 'kategori': category}
        super().__init__(json.dumps(self.details, ensure_ascii=False))
