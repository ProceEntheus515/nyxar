import { useEffect, useRef } from 'react'

/**
 * Detecta cambio de un valor numérico y reaplica `animate-dataFlip` en el nodo.
 * Para métricas en tiempo real; no anima en el montaje inicial.
 *
 * @param {number} value
 * @param {React.RefObject<HTMLElement | null>} elementRef
 */
export function useDataFlip(value, elementRef) {
  const prevValue = useRef(value)

  useEffect(() => {
    if (prevValue.current !== value && elementRef.current) {
      elementRef.current.classList.remove('animate-dataFlip')
      void elementRef.current.offsetWidth
      elementRef.current.classList.add('animate-dataFlip')
      prevValue.current = value
    }
  }, [value, elementRef])
}

/**
 * Delays escalonados para listas al cargar o actualizar.
 *
 * @param {number} count
 * @param {number} [baseDelay=50]
 * @returns {Array<{ style: { animationDelay: string }, className: string }>}
 */
export function useStagger(count, baseDelay = 50) {
  return Array.from({ length: count }, (_, i) => ({
    style: { animationDelay: `${i * baseDelay}ms` },
    className: 'animate-fadeUp',
  }))
}
