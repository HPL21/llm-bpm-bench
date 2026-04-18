<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { CpuIcon, PlusIcon, EditIcon, Trash2Icon, CheckCircle2Icon, XCircleIcon } from 'lucide-vue-next';
import { ModelService, type LLMModel, type LLMModelCreate } from '../services/api';
import ModelModal from '../components/models/ModelModal.vue';

const models = ref<LLMModel[]>([]);
const isModalOpen = ref(false);
const editingModel = ref<LLMModel | null>(null);
const isLoading = ref(true);

const loadModels = async () => {
  isLoading.value = true;
  try {
    models.value = await ModelService.getAllModels();
  } catch (error) {
    console.error("Błąd ładowania modeli:", error);
  } finally {
    isLoading.value = false;
  }
};

const openCreateModal = () => {
  editingModel.value = null;
  isModalOpen.value = true;
};

const openEditModal = (model: LLMModel) => {
  editingModel.value = model;
  isModalOpen.value = true;
};

const handleSaveModel = async (data: LLMModelCreate) => {
  try {
    if (editingModel.value) {
      await ModelService.updateModel(editingModel.value.id, data);
    } else {
      await ModelService.createModel(data);
    }
    isModalOpen.value = false;
    await loadModels();
  } catch (error) {
    console.error("Błąd zapisu:", error);
    alert("Wystąpił błąd podczas zapisywania modelu.");
  }
};

const handleDelete = async (id: string) => {
  if (!confirm("Czy na pewno chcesz usunąć ten model?")) return;
  try {
    await ModelService.deleteModel(id);
    await loadModels();
  } catch (error) {
    console.error("Błąd usuwania:", error);
  }
};

onMounted(loadModels);
</script>

<template>
  <div class="flex flex-col h-full bg-gray-50 text-gray-800 p-6 overflow-y-auto">
    <header class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold flex items-center text-gray-900">
          <CpuIcon class="w-7 h-7 mr-3 text-indigo-600" />
          Modele LLM
        </h1>
        <p class="text-gray-500 mt-1">Zarządzaj połączeniami do modeli językowych wykorzystywanych w testach.</p>
      </div>
      
      <button @click="openCreateModal" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md shadow-sm text-sm font-medium flex items-center transition-colors">
        <PlusIcon class="w-4 h-4 mr-2" />
        Dodaj Model
      </button>
    </header>

    <div v-if="isLoading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
    </div>

    <div v-else-if="models.length === 0" class="text-center py-16 bg-white rounded-xl border border-gray-200 shadow-sm">
      <CpuIcon class="w-16 h-16 mx-auto mb-4 text-gray-300" />
      <h3 class="text-lg font-medium text-gray-900 mb-1">Brak skonfigurowanych modeli</h3>
      <p class="text-gray-500 mb-4">Dodaj swoje API klucze i endpointy, aby móc wykonywać testy.</p>
      <button @click="openCreateModal" class="text-indigo-600 font-medium hover:text-indigo-800">
        + Dodaj nowy model
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      <div v-for="model in models" :key="model.id" class="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex flex-col h-full">
        <div class="p-5 flex-1">
          <div class="flex justify-between items-start mb-3">
            <h2 class="text-lg font-bold text-gray-900 flex items-center gap-2">
              {{ model.name }}
              <CheckCircle2Icon v-if="model.is_active" class="w-4 h-4 text-green-500" title="Aktywny" />
              <XCircleIcon v-else class="w-4 h-4 text-gray-400" title="Nieaktywny" />
            </h2>
            <div class="flex space-x-1">
              <button @click="openEditModal(model)" class="p-1 text-gray-400 hover:text-indigo-600 transition-colors" title="Edytuj">
                <EditIcon class="w-4 h-4" />
              </button>
              <button @click="handleDelete(model.id)" class="p-1 text-gray-400 hover:text-red-500 transition-colors" title="Usuń">
                <Trash2Icon class="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <div class="space-y-2 mt-4 text-sm text-gray-600">
            <p><strong>Dostawca:</strong> <span class="bg-gray-100 px-2 py-0.5 rounded text-xs">{{ model.provider }}</span></p>
            <p><strong>Model ID:</strong> <span class="font-mono text-xs">{{ model.model_identifier }}</span></p>
            <p class="truncate" :title="model.api_base_url"><strong>URL:</strong> {{ model.api_base_url }}</p>
          </div>
        </div>
      </div>
    </div>

    <ModelModal 
      :is-open="isModalOpen" 
      :model-to-edit="editingModel"
      @close="isModalOpen = false" 
      @save="handleSaveModel" 
    />
  </div>
</template>