import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import DataEditor from './components/DataEditor';
import Dashboard from './components/Dashboard';
import { getSettings, saveSettings, translateDatabase } from './api';
import './App.css';

function App() {
  const [activeFile, setActiveFile] = useState('home');
  const [settings, setSettings] = useState({ language: 'en' });
  const [loading, setLoading] = useState(true);
  const [translating, setTranslating] = useState(false);

  const files = [
    'fridge.csv', 'pantry.csv', 'freezer.csv',
    'people.csv', 'ingredients.csv', 'dishes.csv',
    'recipes.csv', 'shopping_habits.csv', 'history.csv', 'meal_plans.csv'
  ];

  useEffect(() => {
    getSettings().then(res => {
      setSettings(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleLanguageChange = async (lang) => {
    const newSettings = { ...settings, language: lang };
    setSettings(newSettings);
    saveSettings(newSettings);

    // Trigger Translation
    setTranslating(true);
    try {
      await translateDatabase(lang);
      alert(`Database translated to ${lang}!`);
      window.location.reload();
    } catch (err) {
      console.error("Translation failed", err);
      alert("Translation failed. Check console.");
    } finally {
      setTranslating(false);
    }
  };

  if (loading) return <div className="app-loading">Loading FoodFlow...</div>;

  return (
    <div className="app-container">
      {/* Sidebar on the Left */}
      <Sidebar
        activeFile={activeFile}
        setActiveFile={setActiveFile}
        files={files}
        settings={settings}
        onLanguageChange={handleLanguageChange}
        translating={translating}
      />

      <main className="main-content">
        <div className="split-view">
          <div className="data-panel">
            {activeFile === 'home' ? (
              <Dashboard language={settings.language} />
            ) : (
              <DataEditor files={[activeFile]} language={settings.language} />
            )}
          </div>
          <div className="chat-panel">
            <ChatInterface language={settings.language} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
