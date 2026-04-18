<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeftIcon, UploadIcon, FileTextIcon, AlertCircleIcon, Trash2Icon, FileIcon } from 'lucide-vue-next';
import { CaseService, FileService, SuiteService, type TestCase, type TestSuite } from '../services/api';

const route = useRoute();
const router = useRouter();
const suiteId = route.params.id as string;

const suite = ref<TestSuite | null>(null);
const cases = ref<TestCase[]>([]);
const collections = ref<string[]>([]);
const isLoading = ref(true);

const isImportModalOpen = ref(false);
const selectedCollection = ref('');
const selectedFile = ref<File | null>(null);
const isImporting = ref(false);
const importError = ref('');
const missingFiles = ref<string[]>([]);

const loadData = async () => {
  isLoading.value = true;
  try {
    const [fetchedSuites, fetchedCases, fetchedFiles] = await Promise.all([
      SuiteService.getAllSuites(),
      CaseService.getSuiteCases(suiteId),
      FileService.getAllFiles()
    ]);
    
    suite.value = fetchedSuites.find(s => s.id === suiteId) || null;
    cases.value = fetchedCases;
    
    const uniqueCollections = new Set(fetchedFiles.map(f => f.collection_name));
    collections.value = Array.from(uniqueCollections);
    
    if (collections.value.length > 0 && !selectedCollection.value) {
      selectedCollection.value = collections.value[0];
    }
  } catch (error) {
    console.error("Błąd ładowania danych:", error);
  } finally {
    isLoading.value = false;
  }
};

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0];
    importError.value = '';
    missingFiles.value = [];
  }
};

const handleImport = async () => {
  if (!selectedFile.value || !selectedCollection.value) return;
  
  isImporting.value = true;
  importError.value = '';
  missingFiles.value = [];
  
  try {
    await CaseService.importCsv(suiteId, selectedCollection.value, selectedFile.value);
    isImportModalOpen.value = false;
    selectedFile.value = null;
    await loadData();
  } catch (error: any) {
    if (error.response?.status === 400) {
      const detail = error.response.data.detail;
      if (typeof detail === 'string') {
        importError.value = detail;
      } else if (detail?.message) {
        importError.value = detail.message;
        if (detail.missing_files) {
          missingFiles.value = detail.missing_files;
        }
      } else {
        importError.value = "Nieprawidłowy format pliku CSV.";
      }
    } else {
      importError.value = "Wystąpił nieoczekiwany błąd serwera.";
    }
  } finally {
    isImporting.value = false;
  }
};

const deleteCase = async (id: string) => {
  if(!confirm("Usunąć ten przypadek testowy?")) return;
  await CaseService.deleteCase(id);
  await loadData();
};

onMounted(loadData);
</script>

<template>
  <div class="flex flex-col h-full flex-1 min-h-0 bg-gray-50 text-gray-800 p-6">
    
    <header class="flex justify-between items-center mb-6 shrink-0">
      <div>
        <button @click="router.push('/suites')" class="text-sm font-medium text-indigo-600 hover:text-indigo-800 flex items-center mb-2">
          <ArrowLeftIcon class="w-4 h-4 mr-1" /> Wróć do zbiorów
        </button>
        <h1 class="text-2xl font-bold flex items-center text-gray-900">
          <ListChecksIcon class="w-7 h-7 mr-3 text-indigo-600" />
          Zbiór: {{ suite?.name || 'Ładowanie...' }}
        </h1>
      </div>
      
      <button @click="isImportModalOpen = true" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md shadow-sm text-sm font-medium flex items-center transition-colors">
        <UploadIcon class="w-4 h-4 mr-2" />
        Importuj CSV
      </button>
    </header>

    <div v-if="isLoading" class="flex justify-center py-12 shrink-0">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
    </div>
    
    <div v-else-if="cases.length === 0" class="text-center py-16 bg-white rounded-xl border border-gray-200 shadow-sm shrink-0">
      <FileTextIcon class="w-16 h-16 mx-auto mb-4 text-gray-300" />
      <h3 class="text-lg font-medium text-gray-900 mb-1">Brak przypadków testowych</h3>
      <p class="text-gray-500 mb-4">Ten zbiór nie ma jeszcze przypisanych testów.</p>
      <button @click="isImportModalOpen = true" class="text-indigo-600 font-medium hover:text-indigo-800">
        Importuj z pliku CSV
      </button>
    </div>

    <div v-else class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-auto flex-1 relative">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50 sticky top-0 z-10 shadow-sm">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Powiązane pliki</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Oczekiwana odp.</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Akcje</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="tc in cases" :key="tc.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">{{ tc.id.substring(0,8) }}</td>
            <td class="px-6 py-4 text-sm text-gray-900">
              <div v-if="tc.files.length === 0" class="text-gray-400 italic">Brak</div>
              <div v-else class="flex flex-wrap gap-1">
                <span v-for="file in tc.files" :key="file.id" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                  <FileIcon class="w-3 h-3 mr-1" />
                  {{ file.filename }}
                </span>
              </div>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500 max-w-xs truncate" :title="tc.expected_output || ''">
              {{ tc.expected_output || 'Brak' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button @click="deleteCase(tc.id)" class="text-red-500 hover:text-red-700">
                <Trash2Icon class="w-4 h-4" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="isImportModalOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <h2 class="text-xl font-bold text-gray-900 mb-4">Import z CSV</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Kolekcja plików</label>
            <select v-model="selectedCollection" class="w-full border border-gray-300 rounded-md shadow-sm px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500">
              <option v-for="col in collections" :key="col" :value="col">{{ col }}</option>
              <option v-if="collections.length === 0" value="" disabled>Brak dostępnych kolekcji</option>
            </select>
            <p class="text-xs text-gray-500 mt-1">Pliki wskazane w arkuszu muszą istnieć w tej kolekcji.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Plik CSV</label>
            <input type="file" accept=".csv" @change="handleFileSelect" class="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"/>
          </div>

          <div v-if="importError" class="p-3 bg-red-50 border border-red-200 rounded-md">
            <div class="flex items-start">
              <AlertCircleIcon class="w-5 h-5 text-red-500 mr-2 mt-0.5 flex-shrink-0" />
              <div>
                <h4 class="text-sm font-medium text-red-800">{{ importError }}</h4>
                <ul v-if="missingFiles.length > 0" class="mt-2 text-xs text-red-700 list-disc list-inside space-y-1 bg-white p-2 rounded border border-red-100 max-h-32 overflow-y-auto font-mono">
                  <li v-for="file in missingFiles" :key="file">{{ file }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 flex justify-end space-x-3">
          <button @click="isImportModalOpen = false" class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
            Anuluj
          </button>
          <button @click="handleImport" :disabled="!selectedFile || isImporting" class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center">
            <div v-if="isImporting" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
            {{ isImporting ? 'Importowanie...' : 'Importuj' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>