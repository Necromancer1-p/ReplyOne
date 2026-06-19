import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { Search, Plus, Trash2, Edit, Loader2, BookOpen, Check, HelpCircle } from 'lucide-react';

interface FAQ {
  id: number;
  category: string;
  question: string;
  content: string;
  is_active: boolean;
}

export const KnowledgeBaseView: React.FC = () => {
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  
  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [editingFaq, setEditingFaq] = useState<FAQ | null>(null);
  const [question, setQuestion] = useState('');
  const [content, setContent] = useState('');
  const [category, setCategory] = useState('faq');
  const [isActive, setIsActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchFaqs = async () => {
    setLoading(true);
    try {
      const data = await api.get<FAQ[]>('/dashboard/knowledge-base');
      setFaqs(data);
    } catch (err) {
      console.error('Failed to load FAQs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFaqs();
  }, []);

  const openCreateModal = () => {
    setModalMode('create');
    setEditingFaq(null);
    setQuestion('');
    setContent('');
    setCategory('faq');
    setIsActive(true);
    setShowModal(true);
  };

  const openEditModal = (faq: FAQ) => {
    setModalMode('edit');
    setEditingFaq(faq);
    setQuestion(faq.question);
    setContent(faq.content);
    setCategory(faq.category);
    setIsActive(faq.is_active);
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !content.trim()) return;

    setSubmitting(true);
    try {
      if (modalMode === 'create') {
        await api.post('/dashboard/knowledge-base', {
          question,
          content,
          category,
          is_active: isActive,
        });
      } else if (modalMode === 'edit' && editingFaq) {
        await api.put(`/dashboard/knowledge-base/${editingFaq.id}`, {
          question,
          content,
          category,
          is_active: isActive,
        });
      }
      setShowModal(false);
      fetchFaqs();
    } catch (err) {
      console.error('Failed to save FAQ:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this FAQ?')) return;
    try {
      await api.delete(`/dashboard/knowledge-base/${id}`);
      fetchFaqs();
    } catch (err) {
      console.error('Failed to delete FAQ:', err);
    }
  };

  // Filter FAQs
  const filteredFaqs = faqs.filter((faq) => {
    const query = searchQuery.toLowerCase();
    const matchesSearch = 
      faq.question.toLowerCase().includes(query) || 
      faq.content.toLowerCase().includes(query);
    
    const matchesCategory = 
      categoryFilter === 'all' || 
      faq.category === categoryFilter;

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="p-lg space-y-lg bg-deepNavy min-h-[calc(100vh-64px)] overflow-y-auto text-cloudWhite">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-md">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-xs">
            <BookOpen className="text-electricBlue" size={24} />
            Knowledge Base (FAQs)
          </h2>
          <p className="text-xs text-darkSecondaryText mt-xs">
            Train your AI Autopilot by defining common questions and answers for customer inquiries.
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="py-md-sm px-md bg-gradient-to-r from-electricBlue to-indigoBrand text-white text-xs font-bold rounded-default shadow-md hover:from-electricBlue/95 hover:to-indigoBrand/95 active:scale-[0.98] transition-all flex items-center gap-xs cursor-pointer border-none"
        >
          <Plus size={16} /> Add FAQ Article
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
            placeholder="Search FAQs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-lg pr-md py-xs bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue text-xs"
          />
        </div>

        {/* Category Filters */}
        <div className="flex gap-xs flex-wrap">
          {['all', 'hours', 'shipping', 'returns', 'faq', 'general'].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-sm py-xs border rounded-default text-xs font-semibold capitalize transition-all cursor-pointer ${
                categoryFilter === cat
                  ? 'bg-indigoBrand/20 border-indigoBrand text-indigoBrand'
                  : 'bg-darkSidebarBg border-darkBorder text-darkSecondaryText hover:text-cloudWhite'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* FAQ Grid list */}
      {loading ? (
        <div className="py-2xl text-center space-y-md">
          <Loader2 className="animate-spin text-indigoBrand mx-auto" size={32} />
          <p className="text-xs text-darkSecondaryText">Fetching FAQ articles...</p>
        </div>
      ) : filteredFaqs.length === 0 ? (
        <div className="bg-darkCardBg/40 border border-darkBorder/60 p-2xl text-center rounded-large space-y-sm">
          <HelpCircle size={40} className="mx-auto text-softSlate" />
          <h3 className="font-bold">No FAQs Found</h3>
          <p className="text-xs text-darkSecondaryText max-w-sm mx-auto">
            {searchQuery || categoryFilter !== 'all' 
              ? 'Try adjusting your search criteria or filters.' 
              : 'Add FAQ articles to train your AI Autopilot with knowledge sources.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
          {filteredFaqs.map((faq) => (
            <div 
              key={faq.id} 
              className={`bg-darkCardBg border p-md rounded-large flex flex-col justify-between transition-all hover:shadow-md ${
                faq.is_active ? 'border-darkBorder' : 'border-darkBorder/40 opacity-70'
              }`}
            >
              <div className="space-y-sm">
                <div className="flex justify-between items-start">
                  <span className="bg-electricBlue/15 text-electricBlue text-[10px] px-sm py-[2px] rounded-pill border border-electricBlue/20 capitalize font-semibold">
                    {faq.category}
                  </span>
                  <span className={`text-[10px] px-sm py-[2px] rounded-pill border font-semibold ${
                    faq.is_active 
                      ? 'bg-successGreen/15 border-successGreen/25 text-successGreen' 
                      : 'bg-softSlate/10 border-softSlate/20 text-darkSecondaryText'
                  }`}>
                    {faq.is_active ? 'Active Training' : 'Inactive'}
                  </span>
                </div>
                <div className="space-y-xs">
                  <h4 className="font-bold text-sm text-cloudWhite leading-snug">{faq.question}</h4>
                  <p className="text-xs text-darkSecondaryText leading-relaxed whitespace-pre-wrap">{faq.content}</p>
                </div>
              </div>

              {/* Action buttons */}
              <div className="mt-lg pt-md border-t border-darkBorder/40 flex justify-end gap-sm">
                <button
                  onClick={() => openEditModal(faq)}
                  className="p-xs text-darkSecondaryText hover:text-cloudWhite bg-darkSidebarBg rounded-default border border-darkBorder cursor-pointer"
                >
                  <Edit size={14} />
                </button>
                <button
                  onClick={() => handleDelete(faq.id)}
                  className="p-xs text-darkSecondaryText hover:text-alertRed bg-darkSidebarBg rounded-default border border-darkBorder cursor-pointer"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Interactive Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-deepNavy/80 backdrop-blur-sm flex items-center justify-center p-md">
          <div className="w-full max-w-lg bg-darkModalBg border border-darkBorder rounded-large p-lg shadow-lg space-y-md">
            <h3 className="font-bold text-lg text-cloudWhite border-b border-darkBorder pb-xs capitalize">
              {modalMode === 'create' ? 'Create FAQ Article' : 'Modify FAQ Article'}
            </h3>

            <form onSubmit={handleSave} className="space-y-md text-xs">
              <div className="grid grid-cols-2 gap-md">
                {/* Category */}
                <div className="space-y-xs">
                  <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full py-md-sm px-md bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite focus:outline-none focus:border-electricBlue text-sm cursor-pointer"
                  >
                    <option value="hours">Hours & Schedule</option>
                    <option value="shipping">Shipping & Delivery</option>
                    <option value="returns">Returns & Refunds</option>
                    <option value="faq">General FAQ</option>
                    <option value="general">Store Policy</option>
                  </select>
                </div>

                {/* Active Status */}
                <div className="space-y-xs flex flex-col justify-end pb-sm">
                  <label className="flex items-center gap-sm cursor-pointer text-sm font-semibold">
                    <input
                      type="checkbox"
                      checked={isActive}
                      onChange={(e) => setIsActive(e.target.checked)}
                      className="w-4 h-4 rounded bg-darkSidebarBg border border-darkBorder text-indigoBrand focus:ring-0 cursor-pointer"
                    />
                    <span>Active Training Source</span>
                  </label>
                </div>
              </div>

              {/* Question */}
              <div className="space-y-xs">
                <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Question</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Do you ship internationally?"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  className="w-full px-md py-md-sm bg-darkSidebarBg border border-darkBorder rounded-default text-cloudWhite placeholder-softSlate focus:outline-none focus:border-electricBlue text-sm"
                />
              </div>

              {/* Answer Content */}
              <div className="space-y-xs">
                <label className="text-xs font-semibold text-darkSecondaryText uppercase tracking-wider">Answer Content</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Write the precise factual reply details enjected into the system prompt context..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
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
                  Save FAQ
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
