<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { BenchmarkService, type BenchmarkRunDetail } from '../services/api';
import { ArrowLeftIcon, BanIcon, RefreshCwIcon } from 'lucide-vue-next';

const props = defineProps<{ id: string }>();
const router = useRouter();

const run = ref<BenchmarkRunDetail | null>(null);
const loading = ref(true);
let pollInterval: number;

const fetchDetails = async () => {
  try {
    run.value = await BenchmarkService.getRunDetails(props.id);
  } catch (error) {
    console.error("Error fetching run details:", error);
  } finally {
    loading.value = false;
  }
};

const cancelRun = async () => {
  if (!confirm("Czy na pewno chcesz anulować ten benchmark?")) return;
  try {
    await BenchmarkService.cancelRun(props.id);
    await fetchDetails();
  } catch (error) {
    alert("Nie udało się anulować benchmarku.");
  }
};

onMounted(() => {
  fetchDetails();
  // Auto-odświeżanie co 3 sekundy jeśli benchmark jest w toku
  pollInterval = setInterval(() => {
    if (run.value && ['PENDING', 'PROCESSING'].includes(run.value.status)) {
      fetchDetails();
    }
  }, 3000);
});

onUnmounted(() => {
  clearInterval(pollInterval);
});

const progress = computed(() => {
  if (!run.value || run.value.total_executions === 0) return 0;
  return Math.round(((run.value.completed_executions + run.value.failed_executions) / run.value.total_executions) * 100);
});

const getStatusColor = (status: string) => {
  switch (status.toUpperCase()) {
    case 'COMPLETED': return 'text-green-600 bg-green-100';
    case 'FAILED': return 'text-red-600 bg-red-100';
    case 'PENDING': return 'text-gray-600 bg-gray-100';
    case 'PROCESSING': return 'text-blue-600 bg-blue-100';
    case 'CANCELLED': return 'text-gray-500 bg-gray-200';
    default: return 'text-gray-600 bg-gray-100';
  }
};
</script>

<template>
  <div class="h-full flex flex-col p-6 bg-gray-50 overflow-y-auto">
    <div v-if="loading" class="flex justify-center items-center h-full">Ładowanie...</div>
    
    <div v-else-if="run" class="max-w-7xl mx-auto w-full space-y-6">
      
      <div class="flex justify-between items-start">
        <div>
          <button @click="router.push('/benchmarks')" class="text-sm text-gray-500 hover:text-indigo-600 flex items-center mb-2">
            <ArrowLeftIcon class="w-4 h-4 mr-1" /> Wróć do listy
          </button>
          <h1 class="text-2xl font-bold text-gray-900">{{ run.name }}</h1>
          <p class="text-sm text-gray-500">ID: {{ run.id }} | Utworzono: {{ new Date(run.created_at).toLocaleString() }}</p>
        </div>
        
        <div class="flex items-center space-x-3">
          <span :class="['px-3 py-1 text-sm font-semibold rounded-full', getStatusColor(run.status)]">
            {{ run.status }}
          </span>
          <button @click="fetchDetails" class="p-2 bg-white border rounded hover:bg-gray-50" title="Odśwież">
            <RefreshCwIcon class="w-4 h-4 text-gray-600" />
          </button>
          <button v-if="['PENDING', 'PROCESSING'].includes(run.status)" @click="cancelRun" class="flex items-center px-3 py-2 bg-red-50 text-red-600 border border-red-200 rounded hover:bg-red-100 text-sm font-medium">
            <BanIcon class="w-4 h-4 mr-1" /> Anuluj
          </button>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow-sm border p-5">
        <div class="flex justify-between text-sm font-medium text-gray-700 mb-2">
          <span>Postęp ({{ progress }}%)</span>
          <span>{{ run.completed_executions + run.failed_executions }} / {{ run.total_executions }}</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2.5 mb-6">
          <div class="bg-indigo-600 h-2.5 rounded-full transition-all duration-500" :style="{ width: progress + '%' }"></div>
        </div>

        <div class="grid grid-cols-4 gap-4 text-center">
          <div class="bg-gray-50 p-3 rounded border">
            <div class="text-2xl font-bold text-gray-800">{{ run.total_executions }}</div>
            <div class="text-xs text-gray-500 uppercase tracking-wide">Wszystkie</div>
          </div>
          <div class="bg-blue-50 p-3 rounded border border-blue-100">
            <div class="text-2xl font-bold text-blue-700">{{ run.pending_executions }}</div>
            <div class="text-xs text-blue-500 uppercase tracking-wide">Oczekujące</div>
          </div>
          <div class="bg-green-50 p-3 rounded border border-green-100">
            <div class="text-2xl font-bold text-green-700">{{ run.completed_executions }}</div>
            <div class="text-xs text-green-600 uppercase tracking-wide">Zakończone</div>
          </div>
          <div class="bg-red-50 p-3 rounded border border-red-100">
            <div class="text-2xl font-bold text-red-700">{{ run.failed_executions }}</div>
            <div class="text-xs text-red-600 uppercase tracking-wide">Błędy</div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-lg shadow-sm border overflow-hidden">
        <div class="px-5 py-4 border-b">
          <h2 class="font-medium text-gray-800">Szczegóły Wykonań</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 text-sm">
            <thead class="bg-gray-50 text-gray-500">
              <tr>
                <th class="px-5 py-3 text-left font-medium">Model LLM (ID)</th>
                <th class="px-5 py-3 text-left font-medium">Test Case (ID)</th>
                <th class="px-5 py-3 text-left font-medium">Status</th>
                <th class="px-5 py-3 text-center font-medium">Wynik (Score)</th>
                <th class="px-5 py-3 text-right font-medium">Czas (ms)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="exec in run.executions" :key="exec.id" class="hover:bg-gray-50">
                <td class="px-5 py-3 font-mono text-xs text-gray-600" :title="exec.llm_model_id">
                  {{ exec.llm_model_id.substring(0, 8) }}...
                </td>
                <td class="px-5 py-3 font-mono text-xs text-gray-600" :title="exec.test_case_id">
                  {{ exec.test_case_id.substring(0, 8) }}...
                </td>
                <td class="px-5 py-3">
                  <span :class="['px-2 py-0.5 rounded text-xs font-medium', getStatusColor(exec.status)]">
                    {{ exec.status }}
                  </span>
                  <div v-if="exec.error_message" class="text-xs text-red-500 mt-1 max-w-xs truncate" :title="exec.error_message">
                    {{ exec.error_message }}
                  </div>
                </td>
                <td class="px-5 py-3 text-center">
                  <span v-if="exec.score !== null" class="font-bold" :class="exec.score > 0.8 ? 'text-green-600' : (exec.score < 0.5 ? 'text-red-600' : 'text-yellow-600')">
                    {{ (exec.score * 100).toFixed(1) }}%
                  </span>
                  <span v-else class="text-gray-400">-</span>
                </td>
                <td class="px-5 py-3 text-right text-gray-600">
                  {{ exec.latency_ms ? `${exec.latency_ms} ms` : '-' }}
                </td>
              </tr>
              <tr v-if="run.executions.length === 0">
                <td colspan="5" class="px-5 py-4 text-center text-gray-500">Brak danych o wykonaniach</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>