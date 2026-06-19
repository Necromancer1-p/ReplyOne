import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { ShoppingBag, Plus, Edit, Trash2, Search, Check, Loader2 } from 'lucide-react';

interface Product {
  id: number;
  name: string;
  description?: string;
  price?: number;
  currency: string;
  stock_status: string;
  image_url?: string;
  is_active: boolean;
}

export const ProductsView: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [stockFilter, setStockFilter] = useState('all');

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState<number | ''>('');
  const [currency, setCurrency] = useState('INR');
  const [stockStatus, setStockStatus] = useState('in_stock');
  const [imageUrl, setImageUrl] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const data = await api.get<Product[]>('/dashboard/products');
      setProducts(data);
    } catch (err) {
      console.error('Failed to load products:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const openCreateModal = () => {
    setModalMode('create');
    setEditingProduct(null);
    setName('');
    setDescription('');
    setPrice('');
    setCurrency('INR');
    setStockStatus('in_stock');
    setImageUrl('');
    setIsActive(true);
    setShowModal(true);
  };

  const openEditModal = (product: Product) => {
    setModalMode('edit');
    setEditingProduct(product);
    setName(product.name);
    setDescription(product.description || '');
    setPrice(product.price || '');
    setCurrency(product.currency);
    setStockStatus(product.stock_status);
    setImageUrl(product.image_url || '');
    setIsActive(product.is_active);
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    const parsedPrice = price === '' ? undefined : Number(price);
    
    try {
      if (modalMode === 'create') {
        await api.post('/dashboard/products', {
          name,
          description,
          price: parsedPrice,
          currency,
          stock_status: stockStatus,
          image_url: imageUrl || undefined,
          is_active: isActive,
        });
      } else if (modalMode === 'edit' && editingProduct) {
        await api.put(`/dashboard/products/${editingProduct.id}`, {
          name,
          description,
          price: parsedPrice,
          currency,
          stock_status: stockStatus,
          image_url: imageUrl || undefined,
          is_active: isActive,
        });
      }
      setShowModal(false);
      fetchProducts();
    } catch (err) {
      console.error('Failed to save product:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this product?')) return;
    try {
      await api.delete(`/dashboard/products/${id}`);
      fetchProducts();
    } catch (err) {
      console.error('Failed to delete product:', err);
    }
  };

  const filteredProducts = products.filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
      (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStock = stockFilter === 'all' || p.stock_status === stockFilter;
    return matchesSearch && matchesStock;
  });

  const getStockBadge = (status: string) => {
    switch (status) {
      case 'in_stock':
        return <span className="bg-successGreen/15 border border-successGreen/25 text-successGreen text-[10px] px-sm py-[2px] rounded-pill font-semibold">In Stock</span>;
      case 'limited':
        return <span className="bg-signalAmber/15 border border-signalAmber/25 text-signalAmber text-[10px] px-sm py-[2px] rounded-pill font-semibold">Limited Stock</span>;
      default:
        return <span className="bg-alertRed/15 border border-alertRed/25 text-alertRed text-[10px] px-sm py-[2px] rounded-pill font-semibold">Out of Stock</span>;
    }
  };

  return (
    <div className="p-lg space-y-lg bg-deepNavy min-h-[calc(100vh-64px)] overflow-y-auto text-cloudWhite">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-md">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-xs">
            <ShoppingBag className="text-electricBlue" size={24} />
            Products Catalog
          </h2>
          <p className="text-xs text-darkSecondaryText mt-xs">
            Upload your shop inventory. AI Autopilot queries this database to answer product availability and pricing inquiries.
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="py-md-sm px-md bg-gradient-to-r from-electricBlue to-indigoBrand text-white text-xs font-bold rounded-default shadow hover:from-electricBlue/95 hover:to-indigoBrand/95 active:scale-[0.98] transition-all flex items-center gap-xs cursor-pointer border-none"
        >
          <Plus size={16} /> Add Product Item
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-md justify-between items-center bg-darkCardBg p-md border border-darkBorder rounded-large">
        <div className="relative w-full md:max-w-sm">
          <div className="absolute inset-y-0 left-0 pl-md-sm flex items-center pointer-events-none text-softSlate">
            <Search size={16} />
          </div>
          <input
            type="text"
            placeholder="Search products..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-lg pr-md py-xs bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue text-xs"
          />
        </div>

        {/* Stock Filters */}
        <div className="flex gap-xs">
          {['all', 'in_stock', 'limited', 'out_of_stock'].map((st) => (
            <button
              key={st}
              onClick={() => setStockFilter(st)}
              className={`px-sm py-xs border rounded-default text-xs font-semibold capitalize transition-all cursor-pointer ${
                stockFilter === st
                  ? 'bg-indigoBrand/20 border-indigoBrand text-indigoBrand'
                  : 'bg-darkSidebarBg border-darkBorder text-darkSecondaryText hover:text-cloudWhite'
              }`}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Product Grid */}
      {loading ? (
        <div className="py-2xl text-center space-y-md">
          <Loader2 className="animate-spin text-indigoBrand mx-auto" size={32} />
          <p className="text-xs text-darkSecondaryText">Loading catalog...</p>
        </div>
      ) : filteredProducts.length === 0 ? (
        <div className="bg-darkCardBg/40 border border-darkBorder/60 p-2xl text-center rounded-large space-y-sm">
          <ShoppingBag size={40} className="mx-auto text-softSlate" />
          <h3 className="font-bold">No Products Found</h3>
          <p className="text-xs text-darkSecondaryText max-w-sm mx-auto">
            {searchQuery || stockFilter !== 'all' 
              ? 'Try adjusting your search criteria or stock filters.' 
              : 'Add products to your catalog to let the AI answer customer inventory inquiries.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-lg">
          {filteredProducts.map((p) => (
            <div 
              key={p.id}
              className={`bg-darkCardBg border p-md rounded-large flex flex-col justify-between transition-all hover:shadow-md ${
                p.is_active ? 'border-darkBorder' : 'border-darkBorder/40 opacity-70'
              }`}
            >
              <div className="space-y-sm">
                {/* Image Placeholder */}
                <div className="aspect-square bg-darkSidebarBg/50 rounded-large border border-darkBorder flex items-center justify-center relative overflow-hidden">
                  {p.image_url ? (
                    <img 
                      src={p.image_url} 
                      alt={p.name}
                      className="object-cover w-full h-full"
                      onError={(e) => {
                        // fallback to placeholder
                        (e.target as HTMLImageElement).src = '';
                      }}
                    />
                  ) : (
                    <ShoppingBag size={32} className="text-softSlate/30" />
                  )}
                  <div className="absolute top-sm left-sm">
                    {getStockBadge(p.stock_status)}
                  </div>
                </div>

                <div className="space-y-xs">
                  <h4 className="font-bold text-sm text-cloudWhite truncate">{p.name}</h4>
                  <div className="text-cyberTeal font-semibold font-mono text-xs">
                    {p.price !== undefined && p.price !== null ? `${p.price} ${p.currency}` : 'Price on request'}
                  </div>
                  <p className="text-xs text-darkSecondaryText line-clamp-3 leading-relaxed">
                    {p.description || 'No description provided.'}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-lg pt-md border-t border-darkBorder/40 flex justify-end gap-sm">
                <button
                  onClick={() => openEditModal(p)}
                  className="p-xs text-darkSecondaryText hover:text-cloudWhite bg-darkSidebarBg rounded-default border border-darkBorder cursor-pointer"
                >
                  <Edit size={14} />
                </button>
                <button
                  onClick={() => handleDelete(p.id)}
                  className="p-xs text-darkSecondaryText hover:text-alertRed bg-darkSidebarBg rounded-default border border-darkBorder cursor-pointer"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Product Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-deepNavy/80 backdrop-blur-sm flex items-center justify-center p-md">
          <div className="w-full max-w-lg bg-darkModalBg border border-darkBorder rounded-large p-lg shadow-lg space-y-md">
            <h3 className="font-bold text-lg text-cloudWhite border-b border-darkBorder pb-xs capitalize">
              {modalMode === 'create' ? 'Add Product to Catalog' : 'Modify Product Item'}
            </h3>

            <form onSubmit={handleSave} className="space-y-md text-xs">
              <div className="grid grid-cols-2 gap-md">
                {/* Name */}
                <div className="space-y-xs col-span-2">
                  <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Product Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Vintage Denim Jacket"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue text-sm"
                  />
                </div>

                {/* Price */}
                <div className="space-y-xs">
                  <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Price</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="1299.00"
                    value={price}
                    onChange={(e) => setPrice(e.target.value === '' ? '' : Number(e.target.value))}
                    className="w-full px-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue text-sm font-mono"
                  />
                </div>

                {/* Stock Status */}
                <div className="space-y-xs">
                  <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Stock Status</label>
                  <select
                    value={stockStatus}
                    onChange={(e) => setStockStatus(e.target.value)}
                    className="w-full py-md-sm px-md bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite focus:outline-none focus:border-electricBlue text-sm cursor-pointer"
                  >
                    <option value="in_stock">In Stock</option>
                    <option value="limited">Limited Quantity</option>
                    <option value="out_of_stock">Out of Stock</option>
                  </select>
                </div>

                {/* Image URL */}
                <div className="space-y-xs col-span-2">
                  <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Image URL (Optional)</label>
                  <input
                    type="url"
                    placeholder="https://example.com/product.jpg"
                    value={imageUrl}
                    onChange={(e) => setImageUrl(e.target.value)}
                    className="w-full px-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue text-sm font-mono"
                  />
                </div>

                {/* Active Status */}
                <div className="space-y-xs col-span-2 flex items-center gap-sm">
                  <label className="flex items-center gap-sm cursor-pointer text-sm font-semibold">
                    <input
                      type="checkbox"
                      checked={isActive}
                      onChange={(e) => setIsActive(e.target.checked)}
                      className="w-4 h-4 rounded bg-darkSidebarBg border border-darkBorder text-indigoBrand focus:ring-0 cursor-pointer"
                    />
                    <span>Visible in Catalog queries</span>
                  </label>
                </div>
              </div>

              {/* Description */}
              <div className="space-y-xs">
                <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Product Description</label>
                <textarea
                  rows={3}
                  placeholder="Key features, colors, material composition, sizes available..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue text-sm resize-none"
                />
              </div>

              {/* Footer */}
              <div className="pt-md border-t border-darkBorder flex justify-end gap-md">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="py-xs px-md border border-darkBorder rounded-default text-cloudWhite hover:bg-darkBorder/40 cursor-pointer text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="py-xs px-lg bg-gradient-to-r from-electricBlue to-indigoBrand text-white font-semibold rounded-default shadow transition-all cursor-pointer flex items-center gap-xs disabled:opacity-50 text-xs"
                >
                  {submitting ? <Loader2 className="animate-spin" size={14} /> : <Check size={14} />}
                  Save Item
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
