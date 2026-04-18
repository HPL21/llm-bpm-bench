<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ModelService, SuiteService, BenchmarkService, type LLMModel, type TestSuite } from '../../services/api';
import { XIcon, PlayIcon } from 'lucide-vue-next';

const emit = defineEmits<{ (e: 'close'): void, (e: 'created'): void }>();

const name = ref('');
const selectedModels = ref<string[]>([]);
const selectedSuites = ref<string[]>([]);

const models = ref<LLMModel[]>([]);
const suites = ref<TestSuite[]>([]);
const isSubmitting = ref(false);

onMounted(async () => {
  try {
    models.value = await ModelService.getAllModels();
    suites.value = await SuiteService.getAllSuites();
  } catch (err) {
    console.error("Failed to load models/suites", err);
  }
});

const submit = async () => {
  if (selectedModels.value.length === 0 || selectedSuites.value.length === 0) return;
  
  isSubmitting.value = true;
  try {
    await BenchmarkService.createRun({
      name: name.value || null,
      model_ids: selectedModels.value,
      suite_ids: selectedSuites.value
    });
    emit('created');
  } catch (error) {
    console.error('Failed to create run:', error);
    alert('Błąd podczas tworzenia benchmarku. Sprawdź logi.');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[90vh]">
      <div class="flex justify-between items-center p-4 border-b">
        <h2 class="text-lg font-semibold">Nowe Uruchomienie Benchmarku</h2>
        <button @click="emit('close')" class="text-gray-500 hover:text-gray-700">
          <XIcon class="w-5 h-5" />
        </button>
      </div>

      <div class="p-4 overflow-y-auto flex-1 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nazwa (opcjonalna)</label>
          <input v-model="name" type="text" placeholder="np. Test Nocny GPT vs Claude" 
                 class="w-full px-3 py-2 border rounded-md focus:ring-indigo-500 focus:border-indigo-500" />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="border rounded-md p-3">
            <h3 class="font-medium text-sm text-gray-700 mb-2">1. Wybierz Modele LLM</h3>
            <div class="space-y-2 max-h-48 overflow-y-auto">
              <label v-for="model in models" :key="model.id" class="flex items-center space-x-2">
                <input type="checkbox" :value="model.id" v-model="selectedModels" class="rounded text-indigo-600 focus:ring-indigo-500" />
                <span class="text-sm">{{ model.name }} ({{ model.provider }})</span>
              </label>
              <div v-if="models.length === 0" class="text-sm text-gray-500">Brak dostępnych modeli.</div>
            </div>
          </div>

          <div class="border rounded-md p-3">
            <h3 class="font-medium text-sm text-gray-700 mb-2">2. Wybierz Zbiory Testowe</h3>
            <div class="space-y-2 max-h-48 overflow-y-auto">
              <label v-for="suite in suites" :key="suite.id" class="flex items-center space-x-2">
                <input type="checkbox" :value="suite.id" v-model="selectedSuites" class="rounded text-indigo-600 focus:ring-indigo-500" />
                <span class="text-sm">{{ suite.name }}</span>
              </label>
              <div v-if="suites.length === 0" class="text-sm text-gray-500">Brak zbiorów testowych.</div>
            </div>
          </div>
        </div>
      </div>

      <div class="p-4 border-t flex justify-end space-x-2 bg-gray-50">
        <button @click="emit('close')" class="px-4 py-2 border rounded-md text-sm font-medium hover:bg-gray-100">
          Anuluj
        </button>
        <button @click="submit" :disabled="isSubmitting || selectedModels.length === 0 || selectedSuites.length === 0" 
                class="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center">
          <PlayIcon class="w-4 h-4 mr-2" />
          {{ isSubmitting ? 'Uruchamianie...' : 'Uruchom Benchmark' }}
        </button>
      </div>
    </div>
  </div>
</template>