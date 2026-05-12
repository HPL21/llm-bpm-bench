<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { BenchmarkService, type BenchmarkRun } from '../services/api';
import { ActivityIcon, PlusIcon, ChevronRightIcon, TrashIcon, DownloadIcon } from 'lucide-vue-next';
import BenchmarkModal from '../components/benchmarks/BenchmarkModal.vue';

const router = useRouter();
const runs = ref<BenchmarkRun[]>([]);
const showModal = ref(false);
const selectedIds = ref<Set<string>>(new Set());

const loadRuns = async () => {
  try {
    runs.value = await BenchmarkService.getAllRuns();
  } catch (error) {
    console.error("Error loading benchmark runs:", error);
  }
};

onMounted(loadRuns);

const handleCreated = () => {
  showModal.value = false;
  loadRuns();
};

const getStatusColor = (status: string) => {
  switch (status.toUpperCase()) {
    case 'COMPLETED': return 'bg-green-100 text-green-800';
    case 'FAILED': return 'bg-red-100 text-red-800';
    case 'PENDING': case 'PROCESSING': return 'bg-blue-100 text-blue-800';
    case 'CANCELLED': return 'bg-gray-100 text-gray-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

const toggleSelection = (id: string) => {
  const newSet = new Set(selectedIds.value);
  if (newSet.has(id)) {
    newSet.delete(id);
  } else {
    newSet.add(id);
  }
  selectedIds.value = newSet;
};

const selectAll = () => {
  if (selectedIds.value.size === runs.value.length) {
    selectedIds.value = new Set();
  } else {
    selectedIds.value = new Set(runs.value.map(r => r.id));
  }
};

const deleteSelected = async () => {
  if (selectedIds.value.size === 0) return;
  
  if (!confirm(`Czy na pewno chcesz usunąć ${selectedIds.value.size} uruchomień benchmarków?`)) {
    return;
  }
  
  try {
    await BenchmarkService.deleteRuns(Array.from(selectedIds.value));
    selectedIds.value = new Set();
    await loadRuns();
  } catch (error) {
    console.error("Error deleting benchmark runs:", error);
  }
};

const exportToExcel = async () => {
  if (selectedIds.value.size === 0) return;
  
  try {
    const blob = await BenchmarkService.exportToExcel(Array.from(selectedIds.value));
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'benchmark_results.xlsx');
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Error exporting to Excel:", error);
    alert("Wystąpił błąd podczas eksportowania do Excel");
  }
};
</script>

<template>
  <div class="h-full flex flex-col p-6 bg-gray-50">
<div class="flex justify-between items-center mb-6">
  <div class="flex items-center text-xl font-semibold text-gray-800">
    <ActivityIcon class="w-6 h-6 mr-2 text-indigo-600" />
    Historia Ewaluacji
  </div>
  <div class="flex gap-2">
    <button 
      v-if="selectedIds.size > 0"
      @click="deleteSelected"
      class="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 flex items-center shadow-sm"
    >
      <TrashIcon class="w-4 h-4 mr-2" />
      Usuń zaznaczone ({{ selectedIds.size }})
    </button>
    <button 
      v-if="selectedIds.size > 0"
      @click="exportToExcel"
      class="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 flex items-center shadow-sm"
    >
      <DownloadIcon class="w-4 h-4 mr-2" />
      Eksportuj do Excel ({{ selectedIds.size }})
    </button>
    <button @click="showModal = true" class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 flex items-center shadow-sm">
      <PlusIcon class="w-4 h-4 mr-2" />
      Nowy Benchmark
    </button>
  </div>
</div>
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 flex flex-col min-h-0 overflow-hidden">
      <div class="overflow-auto flex-1">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50 sticky top-0 z-10 shadow-sm">
            <tr>
              <th class="pl-4 pr-2 py-3 text-left">
                <input 
                  type="checkbox" 
                  :checked="selectedIds.size > 0 && selectedIds.size === runs.length"
                  :indeterminate="selectedIds.size > 0 && selectedIds.size < runs.length"
                  @change="selectAll"
                  class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nazwa</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Liczba Zadań</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data Utworzenia</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Akcje</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr 
              v-for="run in runs" 
              :key="run.id" 
              class="hover:bg-gray-50 cursor-pointer"
              @click="router.push(`/benchmarks/${run.id}`)"
            >
              <td class="pl-4 pr-2 py-4" @click.stop>
                <input 
                  type="checkbox" 
                  :checked="selectedIds.has(run.id)"
                  @change="toggleSelection(run.id)"
                  class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {{ run.name }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="['px-2 inline-flex text-xs leading-5 font-semibold rounded-full', getStatusColor(run.status)]">
                  {{ run.status }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ run.total_executions }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ new Date(run.created_at).toLocaleString() }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <ChevronRightIcon class="w-5 h-5 text-gray-400 inline-block" />
              </td>
            </tr>
            <tr v-if="runs.length === 0">
              <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                Brak uruchomień benchmarków. Kliknij "Nowy Benchmark" aby rozpocząć.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <BenchmarkModal v-if="showModal" @close="showModal = false" @created="handleCreated" />
  </div>
</template>