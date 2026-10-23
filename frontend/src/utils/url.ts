/**
 * Só http(s) vira link clicável. A API já valida `source_url`, mas dados gravados por outro
 * caminho (SQL direto, importações futuras) não podem virar `javascript:` na tela.
 */
export function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.toString() : null
  } catch {
    return null
  }
}
