<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { DatabaseIcon, PlusIcon, EditIcon, Trash2Icon, ListChecksIcon, ShieldCheckIcon } from 'lucide-vue-next';
import { SuiteService, type TestSuite, type TestSuiteCreate } from '../services/api';
import SuiteModal from '../components/suites/SuiteModal.vue';

const router = useRouter();
const suites = ref<TestSuite[]>([]);
const isModalOpen = ref(false);
const editingSuite = ref<TestSuite | null>(null);
const isLoading = ref(true);

const loadSuites = async () => {
  isLoading.value = true;
  try {
    suites.value = await SuiteService.getAllSuites();
  } catch (error) {
    console.error("Błąd ładowania zbiorów:", error);
  } finally {
    isLoading.value = false;
  }
};

const openCreateModal = () => {
  editingSuite.value = null;
  isModalOpen.value = true;
};

const openEditModal = (suite: TestSuite) => {
  editingSuite.value = suite;
  isModalOpen.value = true;
};

const handleSaveSuite = async (data: TestSuiteCreate) => {
  try {
    if (editingSuite.value) {
      await SuiteService.updateSuite(editingSuite.value.id, data);
    } else {
      await SuiteService.createSuite(data);
    }
    isModalOpen.value = false;
    await loadSuites();
  } catch (error) {
    console.error("Błąd zapisu:", error);
    alert("Wystąpił błąd podczas zapisywania zbioru.");
  }
};

const handleDelete = async (id: string) => {
  if (!confirm("Czy na pewno chcesz usunąć ten zbiór? Usunie to również wszystkie przypisane przypadki testowe (wkrótce).")) return;
  try {
    await SuiteService.deleteSuite(id);
    await loadSuites();
  } catch (error) {
    console.error("Błąd usuwania:", error);
  }
};

const goToTestCases = (suiteId: string) => {
  router.push(`/suites/${suiteId}/cases`);
};

onMounted(loadSuites);
</script>

<template>
  <div class="flex flex-col h-full bg-gray-50 text-gray-800 p-6 overflow-y-auto">
    <header class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold flex items-center text-gray-900">
          <DatabaseIcon class="w-7 h-7 mr-3 text-indigo-600" />
          Zbiory Testowe
        </h1>
        <p class="text-gray-500 mt-1">Zarządzaj konfiguracjami i instrukcjami do testowania modeli LLM.</p>
      </div>
      
      <button @click="openCreateModal" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md shadow-sm text-sm font-medium flex items-center transition-colors">
        <PlusIcon class="w-4 h-4 mr-2" />
        Utwórz Zbiór
      </button>
    </header>

    <div v-if="isLoading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
    </div>

    <div v-else-if="suites.length === 0" class="text-center py-16 bg-white rounded-xl border border-gray-200 shadow-sm">
      <DatabaseIcon class="w-16 h-16 mx-auto mb-4 text-gray-300" />
      <h3 class="text-lg font-medium text-gray-900 mb-1">Brak zbiorów testowych</h3>
      <p class="text-gray-500 mb-4">Nie masz jeszcze żadnych skonfigurowanych zbiorów. Utwórz pierwszy, aby zacząć.</p>
      <button @click="openCreateModal" class="text-indigo-600 font-medium hover:text-indigo-800">
        + Utwórz nowy zbiór
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      <div v-for="suite in suites" :key="suite.id" class="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex flex-col h-full">
        <div class="p-5 flex-1">
          <div class="flex justify-between items-start mb-3">
            <h2 class="text-lg font-bold text-gray-900 line-clamp-1" :title="suite.name">{{ suite.name }}</h2>
            <div class="flex space-x-1">
              <button @click="openEditModal(suite)" class="p-1 text-gray-400 hover:text-indigo-600 transition-colors" title="Edytuj">
                <EditIcon class="w-4 h-4" />
              </button>
              <button @click="handleDelete(suite.id)" class="p-1 text-gray-400 hover:text-red-500 transition-colors" title="Usuń">
                <Trash2Icon class="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <p class="text-sm text-gray-600 mb-4 line-clamp-2 h-10" :title="suite.description || ''">
            {{ suite.description || 'Brak opisu.' }}
          </p>

          <div class="flex items-center text-xs font-medium text-indigo-700 bg-indigo-50 px-2 py-1.5 rounded-md w-fit mb-4">
            <ShieldCheckIcon class="w-3.5 h-3.5 mr-1.5" />
            {{ suite.verification_method }}
          </div>
        </div>
        
        <div class="px-5 py-3 border-t border-gray-100 bg-gray-50 rounded-b-xl">
          <button @click="goToTestCases(suite.id)" class="w-full flex items-center justify-center py-2 text-sm font-medium text-slate-700 bg-white border border-gray-300 rounded-md hover:bg-slate-50 hover:text-indigo-600 transition-colors">
            <ListChecksIcon class="w-4 h-4 mr-2" />
            Zarządzaj przypadkami
          </button>
        </div>
      </div>
    </div>

    <SuiteModal 
      :is-open="isModalOpen" 
      :suite-to-edit="editingSuite"
      @close="isModalOpen = false" 
      @save="handleSaveSuite" 
    />
  </div>
</template>