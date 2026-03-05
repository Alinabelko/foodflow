import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
});

export const getSettings = () => api.get('/settings');
export const saveSettings = (settings) => api.post('/settings', settings);
export const getData = (filename) => api.get(`/data/${filename}`);
export const saveData = (filename, data) => api.post(`/data/${filename}`, data);
export const sendChat = (formData) => api.post('/chat', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
});

export const translateDatabase = (lang) => {
    return api.post('/translate_database', { language: lang });
};

export const approveMealPlan = (date) => {
    const formData = new FormData();
    formData.append('date', date);
    return api.post('/meal_plans/approve', formData);
};
export default api;
