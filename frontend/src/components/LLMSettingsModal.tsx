import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Brain,
  Cpu,
  DollarSign,
  Plus,
  Trash2,
  X,
  Loader2,
  Sparkles,
  Play,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronDown,
  Layers,
  History,
  Activity,
  ArrowRight,
} from 'lucide-react';
import {
  getLLMProviders,
  createLLMProvider,
  deleteLLMProvider,
  createLLMModel,
  deleteLLMModel,
  updateLLMModel,
  discoverRemoteLLMModels,
  getLLMUsageSummary,
  testLLMPrompt,
} from '../api/endpoints';
import {
  LLMProvider,
  LLMRemoteDiscoveredModel,
  LLMTestPromptResponse,
  LLMUsageSummary,
} from '../types/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const LLMSettingsModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'providers' | 'usage' | 'playground'>('providers');

  // Add Provider form state
  const [isAddingProvider, setIsAddingProvider] = useState(false);
  const [providerName, setProviderName] = useState('');
  const [providerBaseUrl, setProviderBaseUrl] = useState('https://openrouter.ai/api/v1');
  const [providerApiKey, setProviderApiKey] = useState('');
  const [providerPriority, setProviderPriority] = useState(1);

  // Model discovery state
  const [selectedProviderIdForDiscovery, setSelectedProviderIdForDiscovery] = useState<number | null>(null);

  // Add Model form state
  const [addingModelForProviderId, setAddingModelForProviderId] = useState<number | null>(null);
  const [newModelName, setNewModelName] = useState('');
  const [newModelDisplayName, setNewModelDisplayName] = useState('');
  const [newModelInPrice, setNewModelInPrice] = useState(0.15);
  const [newModelOutPrice, setNewModelOutPrice] = useState(0.60);
  const [newModelPriority, setNewModelPriority] = useState(10);

  // Playground test prompt state
  const [testPrompt, setTestPrompt] = useState('یک فیلم درام فلسفی جذاب از دهه ۹۰ میلادی پیشنهاد بده با توضیح کوتاه.');
  const [testResult, setTestResult] = useState<LLMTestPromptResponse | null>(null);

  // Queries
  const { data: providers = [], isLoading: isLoadingProviders } = useQuery<LLMProvider[]>({
    queryKey: ['llmProviders'],
    queryFn: getLLMProviders,
    enabled: isOpen,
  });

  const { data: usageSummary, isLoading: isLoadingUsage } = useQuery<LLMUsageSummary>({
    queryKey: ['llmUsageSummary'],
    queryFn: () => getLLMUsageSummary(50),
    enabled: isOpen && activeTab === 'usage',
  });

  const { data: discoveredModels = [], isLoading: isLoadingDiscovery } = useQuery<LLMRemoteDiscoveredModel[]>({
    queryKey: ['llmDiscoveredModels', selectedProviderIdForDiscovery],
    queryFn: () => discoverRemoteLLMModels(selectedProviderIdForDiscovery!),
    enabled: !!selectedProviderIdForDiscovery,
  });

  // Mutations
  const createProviderMutation = useMutation({
    mutationFn: createLLMProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llmProviders'] });
      setIsAddingProvider(false);
      setProviderName('');
      setProviderApiKey('');
    },
  });

  const deleteProviderMutation = useMutation({
    mutationFn: deleteLLMProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llmProviders'] });
    },
  });

  const createModelMutation = useMutation({
    mutationFn: createLLMModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llmProviders'] });
      setAddingModelForProviderId(null);
      setNewModelName('');
      setNewModelDisplayName('');
    },
  });

  const deleteModelMutation = useMutation({
    mutationFn: deleteLLMModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llmProviders'] });
    },
  });

  const testPromptMutation = useMutation({
    mutationFn: testLLMPrompt,
    onSuccess: (data) => {
      setTestResult(data);
      queryClient.invalidateQueries({ queryKey: ['llmUsageSummary'] });
    },
    onError: (err: any) => {
      setTestResult({
        success: false,
        provider_name: 'Error',
        model_name: 'None',
        error_message: err.response?.data?.error?.message || err.message,
        prompt_tokens: 0,
        completion_tokens: 0,
        cost_usd: 0,
      });
    },
  });

  if (!isOpen) return null;

  const handleAddProviderSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!providerName.trim() || !providerBaseUrl.trim()) return;
    createProviderMutation.mutate({
      name: providerName.trim(),
      base_url: providerBaseUrl.trim(),
      api_key: providerApiKey.trim() || undefined,
      priority: providerPriority,
    });
  };

  const handleAddModelSubmit = (providerId: number) => {
    if (!newModelName.trim()) return;
    createModelMutation.mutate({
      provider_id: providerId,
      model_name: newModelName.trim(),
      display_name: newModelDisplayName.trim() || newModelName.trim(),
      input_price_per_1m: newModelInPrice,
      output_price_per_1m: newModelOutPrice,
      priority: newModelPriority,
    });
  };

  const handleQuickAddModel = (providerId: number, m: LLMRemoteDiscoveredModel) => {
    createModelMutation.mutate({
      provider_id: providerId,
      model_name: m.id,
      display_name: m.name,
      input_price_per_1m: m.in_price_1m,
      output_price_per_1m: m.out_price_1m,
      priority: 10,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in" dir="rtl">
      <div className="bg-shelf-card border border-shelf-border rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-shelf-border flex items-center justify-between bg-shelf-bg/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">روتر هوش مصنوعی و مدل‌های زبانی (LLM)</h2>
              <p className="text-xs text-slate-400">
                پشتیبانی از چندین ارائه‌دهنده (OpenRouter، OpenAI، Ollama، DeepSeek)، مسیریابی Failover با اولویت، و محاسبه دقیق هزینهٔ توکن‌ها
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/80 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-shelf-border bg-slate-900/60 px-6">
          <button
            onClick={() => setActiveTab('providers')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition ${
              activeTab === 'providers'
                ? 'border-shelf-amber text-shelf-amber'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-4 h-4" />
            ارائه‌دهندگان و زنجیرهٔ مدل‌ها
          </button>
          <button
            onClick={() => setActiveTab('usage')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition ${
              activeTab === 'usage'
                ? 'border-shelf-amber text-shelf-amber'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <DollarSign className="w-4 h-4" />
            آمار مصرف و صورت‌حساب توکن‌ها
          </button>
          <button
            onClick={() => setActiveTab('playground')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition ${
              activeTab === 'playground'
                ? 'border-shelf-amber text-shelf-amber'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Play className="w-4 h-4" />
            آزمایشگاه و تست زنده
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
          {/* TAB 1: PROVIDERS & MODELS */}
          {activeTab === 'providers' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white">ارائه‌دهندگان ثبت‌شده</h3>
                  <p className="text-xs text-slate-400">
                    مدل‌ها به ترتیب اولویت (Priority کمتر = اولویت بالاتر) در فرایندهای تطبیق فیلم و انتخاب کیفیت فراخوانی می‌شوند.
                  </p>
                </div>
                <button
                  onClick={() => setIsAddingProvider(!isAddingProvider)}
                  className="px-3 py-1.5 bg-shelf-amber hover:bg-amber-400 text-black font-bold text-xs rounded-lg flex items-center gap-1.5 transition"
                >
                  <Plus className="w-4 h-4" />
                  افزودن ارائه‌دهنده جدید
                </button>
              </div>

              {/* Add Provider Form */}
              {isAddingProvider && (
                <form
                  onSubmit={handleAddProviderSubmit}
                  className="p-4 rounded-xl bg-slate-900/80 border border-shelf-border space-y-3"
                >
                  <h4 className="text-xs font-bold text-shelf-amber">ثبت ارائه‌دهنده جدید</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">نام ارائه‌دهنده:</label>
                      <input
                        type="text"
                        value={providerName}
                        onChange={(e) => setProviderName(e.target.value)}
                        placeholder="مثال: OpenRouter یا DeepSeek"
                        className="w-full bg-slate-800 border border-shelf-border rounded-lg px-3 py-1.5 text-xs text-white"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">آدرس پایه API (Base URL):</label>
                      <input
                        type="text"
                        value={providerBaseUrl}
                        onChange={(e) => setProviderBaseUrl(e.target.value)}
                        placeholder="https://openrouter.ai/api/v1"
                        className="w-full bg-slate-800 border border-shelf-border rounded-lg px-3 py-1.5 text-xs text-white font-mono"
                        dir="ltr"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">کلید API (اختیاری برای سرورهای محلی):</label>
                      <input
                        type="password"
                        value={providerApiKey}
                        onChange={(e) => setProviderApiKey(e.target.value)}
                        placeholder="sk-..."
                        className="w-full bg-slate-800 border border-shelf-border rounded-lg px-3 py-1.5 text-xs text-white font-mono"
                        dir="ltr"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">اولویت ارائه‌دهنده (۱ = بالاترین):</label>
                      <input
                        type="number"
                        min={1}
                        max={100}
                        value={providerPriority}
                        onChange={(e) => setProviderPriority(parseInt(e.target.value) || 1)}
                        className="w-full bg-slate-800 border border-shelf-border rounded-lg px-3 py-1.5 text-xs text-white font-mono"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setIsAddingProvider(false)}
                      className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
                    >
                      انصراف
                    </button>
                    <button
                      type="submit"
                      disabled={createProviderMutation.isPending}
                      className="px-4 py-1.5 bg-shelf-amber text-black font-bold text-xs rounded-lg flex items-center gap-1.5"
                    >
                      {createProviderMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      ذخیره ارائه‌دهنده
                    </button>
                  </div>
                </form>
              )}

              {/* Providers and their Models list */}
              {isLoadingProviders ? (
                <div className="flex items-center justify-center py-12 text-slate-400 gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-shelf-amber" />
                  <span>در حال دریافت ارائه‌دهندگان...</span>
                </div>
              ) : providers.length === 0 ? (
                <div className="text-center py-12 p-6 rounded-2xl bg-slate-900/40 border border-dashed border-shelf-border text-slate-400 space-y-2">
                  <Brain className="w-8 h-8 mx-auto text-slate-500" />
                  <p className="text-xs">هیچ ارائه‌دهنده هوش مصنوعی تنظیم نشده است.</p>
                  <p className="text-[11px] text-slate-500">برای فعال‌سازی انطباق هوشمند فیلم‌ها و انتخاب خودکار بهترین کیفیت، یک ارائه‌دهنده اضافه کنید.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {providers.map((prov) => (
                    <div
                      key={prov.id}
                      className="p-4 rounded-xl bg-slate-900/50 border border-shelf-border space-y-4"
                    >
                      {/* Provider Header */}
                      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300 font-bold">
                            #{prov.priority}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-white text-sm">{prov.name}</span>
                              {prov.api_key_masked && (
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 font-mono text-slate-400" dir="ltr">
                                  {prov.api_key_masked}
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] font-mono text-slate-400" dir="ltr">
                              {prov.base_url}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() =>
                              setSelectedProviderIdForDiscovery(
                                selectedProviderIdForDiscovery === prov.id ? null : prov.id
                              )
                            }
                            className="px-2.5 py-1 text-xs rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/20 flex items-center gap-1 transition"
                            title="دریافت مدل‌های آنلاین"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            کشف مدل‌ها
                          </button>
                          <button
                            onClick={() =>
                              setAddingModelForProviderId(
                                addingModelForProviderId === prov.id ? null : prov.id
                              )
                            }
                            className="px-2.5 py-1 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center gap-1 transition"
                          >
                            <Plus className="w-3.5 h-3.5" />
                            مدل دستی
                          </button>
                          <button
                            onClick={() => deleteProviderMutation.mutate(prov.id)}
                            className="p-1 text-slate-500 hover:text-red-400 transition"
                            title="حذف ارائه‌دهنده"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Remote Models Discovery Panel */}
                      {selectedProviderIdForDiscovery === prov.id && (
                        <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-500/30 space-y-3">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-purple-300 flex items-center gap-1.5">
                              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                              مدل‌های کشف‌شده از API:
                            </span>
                            {isLoadingDiscovery && (
                              <span className="flex items-center gap-1.5 text-purple-400">
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                در حال جستجو...
                              </span>
                            )}
                          </div>

                          <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                            {discoveredModels.length === 0 && !isLoadingDiscovery && (
                              <p className="text-xs text-slate-500 py-2">مدلی یافت نشد یا سرور پاسخ نداد.</p>
                            )}
                            {discoveredModels.slice(0, 30).map((dm) => (
                              <div
                                key={dm.id}
                                className="flex items-center justify-between p-2 rounded-lg bg-slate-900/80 text-xs border border-slate-800"
                              >
                                <div className="space-y-0.5">
                                  <div className="font-mono text-slate-200" dir="ltr">{dm.id}</div>
                                  <div className="text-[10px] text-slate-400">
                                    قیمت هر میلیون توکن: ورودی ${dm.in_price_1m} / خروجی ${dm.out_price_1m}
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleQuickAddModel(prov.id, dm)}
                                  className="px-2 py-1 bg-shelf-amber text-black font-bold text-[11px] rounded flex items-center gap-1 hover:bg-amber-400 transition"
                                >
                                  <Plus className="w-3 h-3" />
                                  افزودن
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Manual Add Model Form */}
                      {addingModelForProviderId === prov.id && (
                        <div className="p-3 rounded-lg bg-slate-900/90 border border-shelf-border space-y-3">
                          <span className="text-xs font-bold text-slate-300">افزودن دستی مدل به {prov.name}</span>
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">شناسه مدل (API Model Name):</label>
                              <input
                                type="text"
                                value={newModelName}
                                onChange={(e) => setNewModelName(e.target.value)}
                                placeholder="gpt-4o-mini"
                                className="w-full bg-slate-800 border border-shelf-border rounded px-2.5 py-1 text-xs font-mono text-white"
                                dir="ltr"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">نام نمایشی:</label>
                              <input
                                type="text"
                                value={newModelDisplayName}
                                onChange={(e) => setNewModelDisplayName(e.target.value)}
                                placeholder="GPT-4o Mini"
                                className="w-full bg-slate-800 border border-shelf-border rounded px-2.5 py-1 text-xs text-white"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">اولویت (۱ = بالاترین):</label>
                              <input
                                type="number"
                                min={1}
                                max={100}
                                value={newModelPriority}
                                onChange={(e) => setNewModelPriority(parseInt(e.target.value) || 1)}
                                className="w-full bg-slate-800 border border-shelf-border rounded px-2.5 py-1 text-xs text-white font-mono"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">قیمت ورودی ($ / 1M):</label>
                              <input
                                type="number"
                                step="0.01"
                                value={newModelInPrice}
                                onChange={(e) => setNewModelInPrice(parseFloat(e.target.value) || 0)}
                                className="w-full bg-slate-800 border border-shelf-border rounded px-2.5 py-1 text-xs text-white font-mono"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">قیمت خروجی ($ / 1M):</label>
                              <input
                                type="number"
                                step="0.01"
                                value={newModelOutPrice}
                                onChange={(e) => setNewModelOutPrice(parseFloat(e.target.value) || 0)}
                                className="w-full bg-slate-800 border border-shelf-border rounded px-2.5 py-1 text-xs text-white font-mono"
                              />
                            </div>
                          </div>
                          <div className="flex justify-end gap-2 pt-1">
                            <button
                              type="button"
                              onClick={() => setAddingModelForProviderId(null)}
                              className="px-2.5 py-1 text-xs text-slate-400"
                            >
                              انصراف
                            </button>
                            <button
                              type="button"
                              onClick={() => handleAddModelSubmit(prov.id)}
                              className="px-3 py-1 bg-shelf-amber text-black font-bold text-xs rounded"
                            >
                              افزودن مدل
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Configured Models Table */}
                      <div className="space-y-1.5">
                        <span className="text-[11px] font-semibold text-slate-400 block">مدل‌های پیکربندی‌شده:</span>
                        {prov.models.length === 0 ? (
                          <p className="text-xs text-slate-500 py-1">هیچ مدلی برای این ارائه‌دهنده فعال نیست.</p>
                        ) : (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {prov.models.map((m) => (
                              <div
                                key={m.id}
                                className="flex items-center justify-between p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs"
                              >
                                <div className="space-y-0.5">
                                  <div className="flex items-center gap-2">
                                    <span className="font-bold text-white">{m.display_name || m.model_name}</span>
                                    <span className="text-[10px] font-mono text-shelf-amber px-1.5 py-0.2 rounded bg-amber-500/10">
                                      P{m.priority}
                                    </span>
                                  </div>
                                  <div className="text-[10px] font-mono text-slate-400" dir="ltr">{m.model_name}</div>
                                  <div className="text-[10px] text-slate-400">
                                    ${m.input_price_per_1m} / ${m.output_price_per_1m} per 1M
                                  </div>
                                </div>
                                <button
                                  onClick={() => deleteModelMutation.mutate(m.id)}
                                  className="p-1 text-slate-500 hover:text-red-400 transition"
                                  title="حذف مدل"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: USAGE & AUDIT */}
          {activeTab === 'usage' && (
            <div className="space-y-6">
              {isLoadingUsage ? (
                <div className="flex items-center justify-center py-12 text-slate-400 gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-shelf-amber" />
                  <span>در حال دریافت لاگ‌های مصرف...</span>
                </div>
              ) : usageSummary ? (
                <div className="space-y-6">
                  {/* Summary Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-shelf-border space-y-1">
                      <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                        <Activity className="w-3.5 h-3.5 text-shelf-amber" />
                        <span>کل فراخوانی‌ها</span>
                      </div>
                      <div className="text-xl font-bold font-mono text-white">
                        {usageSummary.total_calls.toLocaleString('fa-IR')}
                      </div>
                      <div className="text-[10px] text-emerald-400">
                        {usageSummary.successful_calls} موفق / {usageSummary.failed_calls} ناموفق
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-shelf-border space-y-1">
                      <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                        <Layers className="w-3.5 h-3.5 text-blue-400" />
                        <span>توکن‌های مصرفی</span>
                      </div>
                      <div className="text-xl font-bold font-mono text-white">
                        {(usageSummary.total_prompt_tokens + usageSummary.total_completion_tokens).toLocaleString('fa-IR')}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        ورودی: {usageSummary.total_prompt_tokens.toLocaleString('fa-IR')} | خروجی: {usageSummary.total_completion_tokens.toLocaleString('fa-IR')}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-shelf-border space-y-1">
                      <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                        <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
                        <span>مجموع هزینه دلاری ($)</span>
                      </div>
                      <div className="text-xl font-bold font-mono text-emerald-400" dir="ltr">
                        ${usageSummary.total_cost_usd.toFixed(5)}
                      </div>
                      <div className="text-[10px] text-slate-400">بر مبنای تعرفهٔ دقیق مدل‌ها</div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-shelf-border space-y-1">
                      <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                        <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
                        <span>نرخ موفقیت</span>
                      </div>
                      <div className="text-xl font-bold font-mono text-white">
                        {usageSummary.total_calls > 0
                          ? `${Math.round((usageSummary.successful_calls / usageSummary.total_calls) * 100)}%`
                          : '۱۰۰٪'}
                      </div>
                      <div className="text-[10px] text-slate-400">با اتکا به پشتیبانی Failover</div>
                    </div>
                  </div>

                  {/* Recent Logs Table */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-slate-300 flex items-center gap-2">
                      <History className="w-4 h-4 text-shelf-amber" />
                      آخرین درخواست‌های هوش مصنوعی
                    </h3>
                    <div className="border border-shelf-border rounded-xl overflow-hidden bg-slate-900/40">
                      <div className="overflow-x-auto">
                        <table className="w-full text-right text-xs">
                          <thead className="bg-slate-900/80 text-slate-400 text-[11px] border-b border-shelf-border">
                            <tr>
                              <th className="p-2.5">وضعیت</th>
                              <th className="p-2.5">نوع درخواست</th>
                              <th className="p-2.5">ارائه‌دهنده و مدل</th>
                              <th className="p-2.5">توکن‌ها</th>
                              <th className="p-2.5">هزینه ($)</th>
                              <th className="p-2.5">زمان</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800">
                            {usageSummary.recent_logs.length === 0 ? (
                              <tr>
                                <td colSpan={6} className="p-4 text-center text-slate-500">
                                  هنوز هیچ درخواستی ثبت نشده است.
                                </td>
                              </tr>
                            ) : (
                              usageSummary.recent_logs.map((log) => (
                                <tr key={log.id} className="hover:bg-slate-800/30">
                                  <td className="p-2.5">
                                    {log.success ? (
                                      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
                                        <CheckCircle2 className="w-3 h-3" /> موفق
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-400">
                                        <AlertCircle className="w-3 h-3" /> خطا
                                      </span>
                                    )}
                                  </td>
                                  <td className="p-2.5 font-mono text-[11px] text-slate-300">
                                    {log.agent_type}
                                  </td>
                                  <td className="p-2.5">
                                    <div className="font-semibold text-slate-200">{log.provider_name}</div>
                                    <div className="text-[10px] font-mono text-slate-400" dir="ltr">{log.model_name}</div>
                                  </td>
                                  <td className="p-2.5 font-mono text-slate-300">
                                    {log.prompt_tokens + log.completion_tokens}
                                  </td>
                                  <td className="p-2.5 font-mono text-emerald-400" dir="ltr">
                                    ${log.cost_usd.toFixed(5)}
                                  </td>
                                  <td className="p-2.5 text-slate-400 text-[10px] font-mono" dir="ltr">
                                    {new Date(log.created_at).toLocaleTimeString('fa-IR')}
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* TAB 3: PLAYGROUND */}
          {activeTab === 'playground' && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs text-purple-300 leading-relaxed">
                در این بخش می‌توانید درخواست دلخواه خود را ارسال کنید تا عملکرد زنجیرهٔ Failover و اولویت‌بندی مدل‌ها
                را همراه با محاسبهٔ خودکار هزینه توکن‌ها بررسی نمایید.
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300">متن پرامپت تست:</label>
                <textarea
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-900/80 border border-shelf-border rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-shelf-amber"
                  placeholder="دستور تست را اینجا بنویسید..."
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => testPromptMutation.mutate({ user_prompt: testPrompt })}
                  disabled={testPromptMutation.isPending || !testPrompt.trim()}
                  className="px-5 py-2.5 bg-shelf-amber hover:bg-amber-400 text-black font-bold text-xs rounded-xl flex items-center gap-2 shadow-lg shadow-shelf-amber/10 transition disabled:opacity-50"
                >
                  {testPromptMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      در حال ارسال و فراخوانی زنجیره...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-black" />
                      اجرای تست پرامپت
                    </>
                  )}
                </button>
              </div>

              {testResult && (
                <div className="p-4 rounded-xl bg-slate-900 border border-shelf-border space-y-3 mt-4 animate-fade-in">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2 text-xs">
                    <span className="font-bold flex items-center gap-2 text-white">
                      {testResult.success ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-400" />
                      )}
                      مدل پاسخ‌دهنده: {testResult.provider_name} ({testResult.model_name})
                    </span>
                    <span className="font-mono text-emerald-400" dir="ltr">
                      هزینه: ${testResult.cost_usd.toFixed(6)} | توکن‌ها: {testResult.prompt_tokens}
                    </span>
                  </div>

                  {testResult.error_message ? (
                    <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                      {testResult.error_message}
                    </div>
                  ) : (
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-200 overflow-x-auto whitespace-pre-wrap max-h-60" dir="ltr">
                      {testResult.response_content}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
