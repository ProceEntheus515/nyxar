import IdentityRow from '../data/IdentityRow'

const ROW_PAD = 6

/**
 * Fila virtualizada para la lista de identidades (react-window v2).
 */
export default function IdentityVirtualRow({
  index,
  style,
  ariaAttributes,
  rows,
  selectedId,
  onSelect,
  huntingSet,
}) {
  const row = rows[index]
  if (!row) return null
  return (
    <div style={{ ...style, paddingBottom: ROW_PAD }} {...ariaAttributes}>
      <IdentityRow
        identity={row}
        compact
        selected={selectedId != null && String(selectedId) === String(row.id)}
        inHunting={huntingSet.has(String(row.id))}
        onClick={() => onSelect(row.id)}
      />
    </div>
  )
}
