import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1'; // Dostosuj do swojego środowiska

export const api = axios.create({
    baseURL: API_URL,
});

export interface FileAsset {
    id: string;
    filename: string;
    collection_name: string;
    minio_path: string;
    content_type: string;
    created_at: string;
}

export interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string;
  verification_method: string;
  created_at: string;
  updated_at: string | null;
}

export const FileService = {
    async getAllFiles() {
        const response = await api.get<FileAsset[]>('/files/');
        return response.data;
    },
    
    async uploadFiles(files: File[], collectionName: string) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        formData.append('collection_name', collectionName);
        
        const response = await api.post<FileAsset[]>('/files/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    async deleteFile(id: string) {
        await api.delete(`/files/${id}`);
    },

    async createCollection(name: string) {
        const response = await api.post<FileAsset>('/files/collections', { name });
        return response.data;
    },
};

export type TestSuiteCreate = Omit<TestSuite, 'id' | 'created_at' | 'updated_at'>;

export const SuiteService = {
  async getAllSuites() {
    const response = await api.get<TestSuite[]>('/suites/');
    return response.data;
  },
  
  async createSuite(data: TestSuiteCreate) {
    const response = await api.post<TestSuite>('/suites/', data);
    return response.data;
  },
  
  async updateSuite(id: string, data: Partial<TestSuiteCreate>) {
    const response = await api.put<TestSuite>(`/suites/${id}`, data);
    return response.data;
  },
  
  async deleteSuite(id: string) {
    await api.delete(`/suites/${id}`);
  }
};