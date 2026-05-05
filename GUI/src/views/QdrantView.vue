<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { QdrantService, FileService, ModelService, type LLMModel, type FileAsset } from '../services/api';
import { PlusIcon, TrashIcon, DatabaseIcon, SearchIcon, CpuIcon, FolderIcon, LoaderIcon } from 'lucide-vue-next';

const collections = ref<string[]>([]);
const files = ref<FileAsset[]>([]);
const models = ref<LLMModel[]>([]);
const minioCatalogs = ref<{ name: string; count: number; }[]>([]);

const selectedQdrantCollection = ref<string>('');
const selectedMinioCatalog = ref<string>('');
const selectedModelId = ref<string>('');
const newCollectionName = ref('');
const isCreating = ref(false);
const isIndexing = ref(false);
const isLoadingFiles = ref(false);
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null);

const loadCollections = async () => {
  try {
    const data = await QdrantService.listCollections();
    collections.value = data.collections || [];
  } catch (error) {
    showMessage('error', 'Błąd pobierania kolekcji: ' + error);
  }
};

const loadModels = async () => {
  try {
    models.value = await ModelService.getAllModels();
  } catch (error) {
    showMessage('error', 'Błąd pobierania modeli: ' + error);
  }
};

const loadFiles = async () => {
  isLoadingFiles.value = true;
  try {
    const allFiles = await FileService.getAllFiles();
    files.value = allFiles.filter(f => f.filename !== '.keep');
    const catalogMap = new Map<string, number>();
    files.value.forEach(f => {
      const count = catalogMap.get(f.collection_name) || 0;
      catalogMap.set(f.collection_name, count + 1);
    });
    minioCatalogs.value = Array.from(catalogMap.entries()).map(([name, count]) => ({
      name,
      count
    }));
  } catch (error) {
    showMessage('error', 'Błąd pobierania plików: ' + error);
  } finally {
    isLoadingFiles.value = false;
  }
};

const createCollection = async () => {
  if (!newCollectionName.value.trim()) return;
  isCreating.value = true;
  try {
    await QdrantService.createCollection(newCollectionName.value.trim());
    showMessage('success', `Kolekcja "${newCollectionName.value}" utworzona`);
    newCollectionName.value = '';
    await loadCollections();
  } catch (error) {
    showMessage('error', 'Błąd tworzenia kolekcji: ' + error);
  } finally {
    isCreating.value = false;
  }
};

const deleteCollection = async (name: string) => {
  if (!confirm(`Czy na pewno chcesz usunąć kolekcję "${name}"?`)) return;
  try {
    await QdrantService.deleteCollection(name);
    showMessage('success', `Kolekcja "${name}" usunięta`);
    if (selectedQdrantCollection.value === name) selectedQdrantCollection.value = '';
    await loadCollections();
  } catch (error) {
    showMessage('error', 'Błąd usuwania kolekcji: ' + error);
  }
};

const getFilesInMinioCatalog = () => {
  if (!selectedMinioCatalog.value) return [];
  return files.value.filter(f => f.collection_name === selectedMinioCatalog.value);
};

const indexCatalog = async () => {
  if (!selectedQdrantCollection.value) {
    showMessage('error', 'Wybierz kolekcję Qdrant (gdzie zapisać chunki)');
    return;
  }
  if (!selectedMinioCatalog.value) {
    showMessage('error', 'Wybierz katalog MinIO (skąd brać pliki)');
    return;
  }
  if (!selectedModelId.value) {
    showMessage('error', 'Wybierz model embeddingowy');
    return;
  }

  const filesInCatalog = getFilesInMinioCatalog();
  if (filesInCatalog.length === 0) {
    showMessage('error', 'Wybrany katalog MinIO nie ma plików');
    return;
  }

  if (!confirm(`Zindeksować ${filesInCatalog.length} plików z katalogu "${selectedMinioCatalog.value}" do kolekcji "${selectedQdrantCollection.value}"?`)) return;

  isIndexing.value = true;
  try {
    const result = await QdrantService.indexCollection(
      selectedQdrantCollection.value,
      selectedModelId.value,
      selectedMinioCatalog.value
    );
    showMessage('success', `Zindeksowano: ${result.message}`);
  } catch (error) {
    showMessage('error', 'Błąd indeksowania: ' + error);
  } finally {
    isIndexing.value = false;
  }
};

const showMessage = (type: 'success' | 'error', text: string) => {
  message.value = { type, text };
  setTimeout(() => { message.value = null; }, 5000);
};

onMounted(() => {
  loadCollections();
  loadModels();
  loadFiles();
});
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold mb-6 flex items-center gap-2">
      <DatabaseIcon class="w-7 h-7 text-indigo-500" />
      Zarządzanie Qdrant (RAG)
    </h1>

    <div v-if="message" :class="[
      'mb-4 p-3 rounded-md text-sm',
      message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
    ]">
      {{ message.text }}
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="bg-white p-4 rounded-lg shadow">
        <h2 class="text-lg font-semibold mb-4">Kolekcje Qdrant</h2>

        <div class="flex gap-2 mb-4">
          <input
            v-model="newCollectionName"
            type="text"
            placeholder="Nazwa nowej kolekcji"
            class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
            @keyup.enter="createCollection"
          />
          <button
            @click="createCollection"
            :disabled="isCreating || !newCollectionName.trim()"
            class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 text-sm"
          >
            <PlusIcon class="w-4 h-4 inline" /> Utwórz
          </button>
        </div>

        <div class="space-y-2 max-h-64 overflow-y-auto">
          <div
            v-for="col in collections"
            :key="col"
            @click="selectedQdrantCollection = col"
            :class="[
              'p-3 border rounded-md cursor-pointer flex justify-between items-center',
              selectedQdrantCollection === col ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:bg-gray-50'
            ]"
          >
            <div class="flex items-center gap-2">
              <DatabaseIcon class="w-4 h-4 text-gray-500" />
              <span class="font-medium">{{ col }}</span>
            </div>
            <button
              @click.stop="deleteCollection(col)"
              class="text-red-500 hover:text-red-700"
              title="Usuń kolekcję"
            >
              <TrashIcon class="w-4 h-4" />
            </button>
          </div>
          <div v-if="collections.length === 0" class="text-gray-500 text-sm text-center py-4">
            Brak kolekcji. Utwórz pierwszą kolekcję powyżej.
          </div>
        </div>
      </div>

      <div class="bg-white p-4 rounded-lg shadow">
        <h2 class="text-lg font-semibold mb-4">Indeksowanie katalogu</h2>

        <div class="mb-4 p-3 bg-gray-50 rounded-md">
          <label class="text-sm font-medium text-gray-700">Kolekcja Qdrant (gdzie zapisać):</label>
          <div class="mt-1 font-medium text-indigo-600">{{ selectedQdrantCollection || 'Wybierz z lewej strony' }}</div>
        </div>

        <div class="mb-4">
          <label class="text-sm font-medium text-gray-700 mb-1 block">Katalog MinIO (skąd brać pliki):</label>
          <div class="flex items-center gap-2">
            <FolderIcon class="w-4 h-4 text-gray-500" />
            <select
              v-model="selectedMinioCatalog"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
            >
              <option value="">-- Wybierz katalog --</option>
              <option v-for="cat in minioCatalogs" :key="cat.name" :value="cat.name">
                {{ cat.name }} ({{ cat.count }} {{ cat.count === 1 ? 'plik' : 'pliki' }})
              </option>
            </select>
          </div>
        </div>

        <div v-if="selectedMinioCatalog" class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <label class="text-sm font-medium text-gray-700">Pliki w katalogu:</label>
            <span class="text-xs text-gray-500">{{ getFilesInMinioCatalog().length }} plików</span>
          </div>
          <div class="max-h-32 overflow-y-auto border border-gray-200 rounded-md p-2">
            <div v-if="isLoadingFiles" class="text-center py-2">
              <LoaderIcon class="w-4 h-4 inline animate-spin" />
            </div>
            <div v-else-if="getFilesInMinioCatalog().length === 0" class="text-gray-500 text-xs text-center py-2">
              Brak plików w tym katalogu
            </div>
            <div v-else v-for="file in getFilesInMinioCatalog()" :key="file.id" class="text-xs py-1 flex items-center gap-1">
              <FolderIcon class="w-3 h-3 text-gray-400" />
              {{ file.filename }}
            </div>
          </div>
        </div>

        <div class="mb-4">
          <label class="text-sm font-medium text-gray-700 mb-1 block">Model embeddingowy:</label>
          <div class="flex items-center gap-2">
            <CpuIcon class="w-4 h-4 text-gray-500" />
            <select
              v-model="selectedModelId"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
            >
              <option value="">-- Wybierz model --</option>
              <option v-for="model in models" :key="model.id" :value="model.id">
                {{ model.name }} ({{ model.provider }})
              </option>
            </select>
          </div>
        </div>

        <button
          @click="indexCatalog"
          :disabled="isIndexing || !selectedQdrantCollection || !selectedMinioCatalog || !selectedModelId"
          class="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 text-sm"
        >
          <SearchIcon class="w-4 h-4 inline mr-1" />
          {{ isIndexing ? 'Indeksowanie...' : `Zindeksuj katalog "${selectedMinioCatalog}"` }}
        </button>
      </div>
    </div>
  </div>
</template>
