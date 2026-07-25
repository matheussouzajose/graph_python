#!/usr/bin/env bash
# Build + push das imagens para o registry.
#
#   ./deploy/release-api.sh              # tag = SHA curto do git (ex.: a1b2c3d) + latest
#   ./deploy/release-api.sh v1.0.0       # tag = v1.0.0 + latest
#
# Requer: docker login registry.msouzajose.tech (uma vez).
set -euo pipefail

REGISTRY="registry.msouzajose.tech"
API_IMAGE="${REGISTRY}/oraculo-graph-api"
FRONTEND_IMAGE="${REGISTRY}/oraculo-graph-frontend"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-/api/v1}"

# Versão: 1º argumento, senão o SHA curto do commit atual.
VERSION="${1:-$(git rev-parse --short HEAD)}"
VCS_REF="$(git rev-parse --short HEAD)"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Recusa build com árvore suja quando a tag NÃO é um SHA (release nomeada
# precisa ser reproduzível a partir de um commit limpo).
if [ "${VERSION}" != "${VCS_REF}" ] && ! git diff-index --quiet HEAD --; then
    echo "ERRO: working tree suja — commite antes de uma release nomeada (${VERSION})." >&2
    exit 1
fi

echo ">> Building ${API_IMAGE}:${VERSION} e :latest"
docker build \
    --build-arg VERSION="${VERSION}" \
    --build-arg VCS_REF="${VCS_REF}" \
    --build-arg BUILD_DATE="${BUILD_DATE}" \
    -t "${API_IMAGE}:${VERSION}" \
    -t "${API_IMAGE}:latest" \
    . \
    --no-cache

echo ">> Building ${FRONTEND_IMAGE}:${VERSION} e :latest"
docker build \
    --build-arg VITE_API_BASE_URL="${VITE_API_BASE_URL}" \
    -t "${FRONTEND_IMAGE}:${VERSION}" \
    -t "${FRONTEND_IMAGE}:latest" \
    ./frontend \
    --no-cache

echo ">> Pushing ${API_IMAGE}:${VERSION} e :latest"
docker push "${API_IMAGE}:${VERSION}"
docker push "${API_IMAGE}:latest"

echo ">> Pushing ${FRONTEND_IMAGE}:${VERSION} e :latest"
docker push "${FRONTEND_IMAGE}:${VERSION}"
docker push "${FRONTEND_IMAGE}:latest"

echo ">> OK. Deploy com:"
echo "   IMAGE_TAG=${VERSION} docker compose -f docker-compose.PROD.yml pull"
echo "   IMAGE_TAG=${VERSION} docker compose -f docker-compose.PROD.yml up -d"
