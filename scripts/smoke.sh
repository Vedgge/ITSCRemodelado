#!/usr/bin/env bash
# End-to-end smoke test against a running stack.
#
# Catches the entire class of "green in pytest, broken in the container":
# wrong paths once the package is installed, missing runtime libraries,
# non-writable directories, proxy header handling.
#
# Usage: scripts/smoke.sh [base-url]
set -euo pipefail

BASE="${1:-http://localhost:8000}"
JAR="$(mktemp)"
FAILURES=0
trap 'rm -f "$JAR"' EXIT

pass() { printf '  \033[32mok\033[0m   %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

check_status() {
    local path="$1" expected="$2"
    local got
    got=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$path")
    [ "$got" = "$expected" ] && pass "$path -> $got" || fail "$path -> $got (expected $expected)"
}

check_header() {
    local path="$1" header="$2" needle="$3"
    if curl -sI "$BASE$path" | grep -qi "$header.*$needle"; then
        pass "$header on $path"
    else
        fail "$header missing or wrong on $path"
    fi
}

echo "== readiness =="
check_status /healthz 200
check_status /readyz 200
curl -s "$BASE/readyz" | grep -q '"status": *"ok"' && pass "readyz reports ok" || fail "readyz not ok"

echo "== public pages =="
for p in / /nosotros /carreras /carreras/enfermeria /estudiantes /preguntas-frecuentes \
         /fotogaleria /cooperadora /mapa-del-sitio /novedades/ /contacto/ /ingresar; do
    check_status "$p" 200
done

echo "== document repositories =="
for p in /convocatorias/ /convocatorias/vigentes/ /resoluciones/ /actas-dictamenes/ \
         /materiales-para-descargar/ /mesas-de-examen/; do
    check_status "$p" 200
done

echo "== legacy redirects =="
for p in /static/index.html /static/FAQ.html /static/nosotros.html /static/mostrar-datos-contacto.html; do
    check_status "$p" 301
done

echo "== errors =="
check_status /no-existe 404
check_status /static/inventado.html 404

echo "== authorisation =="
check_status /admin/ 302
check_status /admin/novedades 302

echo "== security headers =="
check_header / "content-security-policy" "default-src 'self'"
check_header / "x-content-type-options" "nosniff"
check_header / "x-frame-options" "DENY"
check_header / "referrer-policy" "strict-origin"
if curl -sI "$BASE/" | grep -qi "access-control-allow-origin"; then
    fail "CORS header present (it must not be)"
else
    pass "no CORS header"
fi
if curl -sI "$BASE/" | grep -i "content-security-policy" | grep -q "unsafe-inline"; then
    fail "CSP contains unsafe-inline"
else
    pass "CSP has no unsafe-inline"
fi

echo "== api =="
check_status /api/v1/novedades 200
curl -s "$BASE/api/v1/novedades" | grep -q '"meta"' && pass "api is paginated" || fail "api meta missing"

echo "== no traceback ever reaches a user =="
if curl -s "$BASE/no-existe" | grep -qi "traceback"; then
    fail "traceback leaked on 404"
else
    pass "404 page has no traceback"
fi

echo
if [ "$FAILURES" -eq 0 ]; then
    printf '\033[32mSMOKE PASSED\033[0m\n'
else
    printf '\033[31mSMOKE FAILED: %d check(s)\033[0m\n' "$FAILURES"
    exit 1
fi
