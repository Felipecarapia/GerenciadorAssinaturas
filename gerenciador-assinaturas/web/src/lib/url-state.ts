import { useCallback, useEffect, useState } from 'react'

export function useUrlState(key: string, fallback: string) {
  const read = useCallback(() => new URLSearchParams(window.location.search).get(key) ?? fallback, [fallback, key])
  const [value, setValue] = useState<string>(read)

  useEffect(() => {
    const syncFromHistory = () => setValue(read())
    window.addEventListener('popstate', syncFromHistory)
    return () => window.removeEventListener('popstate', syncFromHistory)
  }, [read])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (value === fallback || !value) params.delete(key)
    else params.set(key, value)
    const search = params.toString()
    window.history.replaceState(window.history.state, '', `${window.location.pathname}${search ? `?${search}` : ''}${window.location.hash}`)
  }, [fallback, key, value])

  return [value, setValue] as const
}
