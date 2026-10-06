import type { WarrantyPrice } from '../api/warrantyApi'

interface WarrantyPriceListProps {
  prices: WarrantyPrice[]
  loading: boolean
  onEdit: (priceId: number) => void
}

export default function WarrantyPriceList({ prices, loading, onEdit }: WarrantyPriceListProps) {
  return (
    <section className="product-list-panel warranty-price-list">
      <div className="section-heading section-heading--list">
        <div>
          <p className="eyebrow">Price periods</p>
          <h2>Warranty prices</h2>
        </div>
        <span>{prices.length} records</span>
      </div>
      {loading ? <div className="table-loading">Loading warranty prices...</div> : prices.length === 0 ? (
        <div className="empty-state">No prices have been added for this option.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Price</th><th>Valid from</th><th>Valid to</th><th>Action</th></tr></thead>
            <tbody>
              {prices.map((price) => (
                <tr key={price.id}>
                  <td className="product-name-cell">{Number(price.price).toFixed(2)}</td>
                  <td>{price.valid_from}</td>
                  <td>{price.valid_to ?? 'No end date'}</td>
                  <td><button type="button" className="row-action" onClick={() => onEdit(price.id)}>Edit</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}