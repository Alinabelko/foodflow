import React from 'react';
import { Settings, FolderOpen, Globe } from 'lucide-react';
import { translations as t } from '../translations';

const Sidebar = ({ activeFile, setActiveFile, files, settings, onLanguageChange, translating }) => {
    const lang = settings.language || 'en';
    const text = t[lang] || t.en;

    const languages = [
        { code: 'en', label: text.english },
        { code: 'ru', label: text.russian },
        { code: 'es', label: text.spanish }
    ];

    return (
        <div className="sidebar">
            <div className="logo">
                <span className="icon">🥗</span>
                <span className="text">FoodFlow</span>
            </div>

            <nav>
                <div className="section-title">
                    <FolderOpen size={16} />
                    <span>{text.databases}</span>
                </div>
                <button
                    className={activeFile === 'home' ? 'active' : ''}
                    onClick={() => setActiveFile('home')}
                >
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                        <span style={{ fontSize: '1.2rem' }}>🏠</span>
                        <span>{text.dashboard}</span>
                    </div>
                </button>
                {files.map(file => {
                    const key = file.replace('.csv', '');
                    return (
                        <button
                            key={file}
                            className={activeFile === file ? 'active' : ''}
                            onClick={() => setActiveFile(file)}
                        >
                            {text[key] || key.replace('_', ' ').replace(/(^\w|\s\w)/g, m => m.toUpperCase())}
                        </button>
                    );
                })}
            </nav>

            <div className="settings">
                <div className="section-title">
                    <Settings size={16} />
                    <span>{text.settings}</span>
                </div>
                <div className="setting-item">
                    <Globe size={16} />
                    <select
                        value={settings.language || 'en'}
                        onChange={(e) => onLanguageChange(e.target.value)}
                        disabled={translating}
                    >
                        {languages.map(lang => (
                            <option key={lang.code} value={lang.code}>{lang.label}</option>
                        ))}
                    </select>
                    {translating && <div style={{ fontSize: '0.8rem', color: 'var(--accent)', marginTop: '5px' }}>{text.translating}</div>}
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
