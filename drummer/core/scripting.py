import json
from typing import Any

import quickjs
from pydantic import BaseModel

from drummer.core.debugger import suggest

_DEFAULT_TIMEOUT_MS = 5000

# Pure-JS SHA-256 + HMAC-SHA-256 (no Python callbacks needed, safe under time limits).
_HMAC_SHA256_JS = r"""
var __hmacSha256 = (function () {
    var K = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
        0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
        0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];

    function sha256bytes(bytes) {
        var H = [
            0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
            0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
        ];
        var bitLen = bytes.length * 8;
        bytes.push(0x80);
        while (bytes.length % 64 !== 56) bytes.push(0);
        bytes.push(
            0, 0, 0, 0,
            (bitLen / 0x100000000) & 0xff,
            (bitLen / 0x1000000) & 0xff,
            (bitLen / 0x10000) & 0xff,
            (bitLen / 0x100) & 0xff
        );
        bytes[bytes.length - 4] = (bitLen >>> 24) & 0xff;
        bytes[bytes.length - 3] = (bitLen >>> 16) & 0xff;
        bytes[bytes.length - 2] = (bitLen >>> 8) & 0xff;
        bytes[bytes.length - 1] = bitLen & 0xff;
        for (var i = 0; i < bytes.length; i += 64) {
            var W = [];
            for (var j = 0; j < 16; j++) {
                W[j] = (bytes[i + j * 4] << 24) | (bytes[i + j * 4 + 1] << 16) |
                        (bytes[i + j * 4 + 2] << 8) | bytes[i + j * 4 + 3];
            }
            for (var j = 16; j < 64; j++) {
                var w15 = W[j - 15], w2 = W[j - 2];
                var s0 = ((w15>>>7)|(w15<<25)) ^ ((w15>>>18)|(w15<<14)) ^ (w15>>>3);
                var s1 = ((w2>>>17)|(w2<<15)) ^ ((w2>>>19)|(w2<<13)) ^ (w2>>>10);
                W[j] = (W[j - 16] + s0 + W[j - 7] + s1) | 0;
            }
            var a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
            for (var j = 0; j < 64; j++) {
                var S1 = ((e>>>6)|(e<<26)) ^ ((e>>>11)|(e<<21)) ^ ((e>>>25)|(e<<7));
                var ch = (e & f) ^ ((~e) & g);
                var t1 = (h + S1 + ch + K[j] + W[j]) | 0;
                var S0 = ((a>>>2)|(a<<30)) ^ ((a>>>13)|(a<<19)) ^ ((a>>>22)|(a<<10));
                var maj = (a & b) ^ (a & c) ^ (b & c);
                var t2 = (S0 + maj) | 0;
                h=g; g=f; f=e; e=(d+t1)|0; d=c; c=b; b=a; a=(t1+t2)|0;
            }
            H[0]=(H[0]+a)|0; H[1]=(H[1]+b)|0; H[2]=(H[2]+c)|0; H[3]=(H[3]+d)|0;
            H[4]=(H[4]+e)|0; H[5]=(H[5]+f)|0; H[6]=(H[6]+g)|0; H[7]=(H[7]+h)|0;
        }
        var hex = '';
        for (var i = 0; i < 8; i++) {
            hex += ('0000000' + (H[i] >>> 0).toString(16)).slice(-8);
        }
        return hex;
    }

    function strToBytes(s) {
        var b = [];
        for (var i = 0; i < s.length; i++) {
            var c = s.charCodeAt(i);
            if (c < 128) {
                b.push(c);
            } else if (c < 2048) {
                b.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f));
            } else if (c >= 0xD800 && c <= 0xDBFF && i + 1 < s.length) {
                var c2 = s.charCodeAt(++i);
                var cp = 0x10000 + ((c - 0xD800) << 10) + (c2 - 0xDC00);
                b.push(0xf0|(cp>>18), 0x80|((cp>>12)&0x3f), 0x80|((cp>>6)&0x3f), 0x80|(cp&0x3f));
            } else {
                b.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
            }
        }
        return b;
    }

    function hexToBytes(h) {
        var b = [];
        for (var i = 0; i < h.length; i += 2) {
            b.push(parseInt(h.substr(i, 2), 16));
        }
        return b;
    }

    return function hmacSha256(key, data) {
        var blockSize = 64;
        var keyBytes = strToBytes(key);
        if (keyBytes.length > blockSize) {
            keyBytes = hexToBytes(sha256bytes(keyBytes));
        }
        while (keyBytes.length < blockSize) keyBytes.push(0);
        var ipad = keyBytes.map(function (b) { return b ^ 0x36; });
        var opad = keyBytes.map(function (b) { return b ^ 0x5c; });
        return sha256bytes(opad.concat(hexToBytes(sha256bytes(ipad.concat(strToBytes(data))))));
    };
})();
"""

_DM_SETUP_PRE = """
Object.defineProperty(dm, 'response', {
    get: function () {
        throw new Error(
            "dm.response is not available in pre-scripts — move this to a post-script."
        );
    },
    enumerable: false,
    configurable: false
});
"""

_DM_SETUP_POST = """
dm.response = {
    status: __resp_status,
    headers: __resp_headers,
    text: function () { return __resp_body; },
    json: function () { return JSON.parse(__resp_body); }
};
"""


class ScriptResult(BaseModel):
    logs: list[str] = []
    error: str | None = None
    suggestion: str | None = None
    env_mutations: dict[str, str] = {}
    request_mutations: dict[str, Any] = {}


def run_script(
    script: str,
    *,
    variables: dict[str, str],
    request_fields: dict[str, Any],
    response_fields: dict[str, Any] | None,
    timeout_ms: int = _DEFAULT_TIMEOUT_MS,
) -> ScriptResult:
    ctx = quickjs.Context()

    # Load pure-JS HMAC helper (no Python callbacks, safe under time limits).
    ctx.eval(_HMAC_SHA256_JS)

    # Inject initial environment variables into JS state.
    ctx.set("__init_env", ctx.parse_json(json.dumps(variables)))

    # Inject request object.
    ctx.set("__req", ctx.parse_json(json.dumps(request_fields)))

    # Inject response fields for post-scripts.
    if response_fields is not None:
        ctx.set("__resp_status", response_fields["status"])
        ctx.set("__resp_body", response_fields["body"])
        ctx.set("__resp_headers", ctx.parse_json(json.dumps(response_fields["headers"])))

    # Build the dm API entirely in JS so no Python callbacks are needed at
    # execution time (which would be blocked by the time limit).
    ctx.eval("""
var __logs = [];
var __env_mutations = {};
var __current_env = (function () {
    var e = {};
    for (var k in __init_env) { e[k] = __init_env[k]; }
    return e;
})();

var dm = {
    env: {
        get: function (k) {
            var v = __current_env[k];
            return v !== undefined ? String(v) : null;
        },
        set: function (k, v) {
            var sv = String(v);
            __current_env[k] = sv;
            __env_mutations[k] = sv;
        }
    },
    request: __req,
    crypto: {
        hmacSha256: function (key, data) {
            return __hmacSha256(key, data);
        }
    },
    console: {
        log: function () {
            var a = [];
            for (var i = 0; i < arguments.length; i++) {
                a.push(String(arguments[i]));
            }
            __logs.push(a.join(' '));
        }
    }
};
""")

    ctx.eval(_DM_SETUP_POST if response_fields is not None else _DM_SETUP_PRE)

    ctx.set_time_limit(timeout_ms / 1000)
    try:
        ctx.eval(script)
    except quickjs.JSException as exc:
        ctx.set_time_limit(-1)
        error = str(exc)
        return ScriptResult(logs=[], error=error, suggestion=suggest(error))
    ctx.set_time_limit(-1)

    logs: list[str] = json.loads(str(ctx.eval("JSON.stringify(__logs)")))
    env_mutations: dict[str, str] = json.loads(str(ctx.eval("JSON.stringify(__env_mutations)")))
    request_mutations: dict[str, Any] = json.loads(str(ctx.eval("JSON.stringify(__req)")))

    return ScriptResult(logs=logs, env_mutations=env_mutations, request_mutations=request_mutations)
