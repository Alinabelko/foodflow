import React, { useState, useEffect } from 'react';
import { Save, RefreshCw } from 'lucide-react';
import { getData, saveData } from '../api';
import { translations as t } from '../translations';
import './DataEditor.css';

const DataEditor = ({ files, language }) => {
    // files prop is now single element array from App.jsx, but we keep structure
    const activeFile = files[0];
    const text = t[language] || t.en;
    const [data, setData] = useState([]);
    const [headers, setHeaders] = useState([]);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchData(activeFile);
    }, [activeFile]);

    const fetchData = async (filename) => {
        setLoading(true);
        try {
            const res = await getData(filename);
            setData(res.data);
            if (res.data.length > 0) {
                setHeaders(Object.keys(res.data[0]));
            } else {
                // Simple heuristic for headers if empty, based on filename 
                // In real app, cleaner to fetch schema endpoint.
                // For now, if empty, we might show "Empty" message or empty headers.
                if (filename.includes("fridge")) setHeaders(["item", "bought_date", "expiry_date", "expected_eat_date"]);
                else if (filename.includes("meal_plans")) setHeaders(["date", "meal_type", "dish_name", "notes", "status"]);
                else if (filename.includes("history")) setHeaders(["item", "action", "date", "quantity", "calories", "protein", "fats", "carbs"]);
                else if (filename.includes("people")) setHeaders(["name", "health_issues", "diet_issues", "goals"]);
                else setHeaders(["item", "description"]);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await saveData(activeFile, data);
            alert('Saved!');
        } catch (err) {
            alert('Error saving');
        } finally {
            setSaving(false);
        }
    };

    const handleChange = (rowIdx, col, val) => {
        const newData = [...data];
        newData[rowIdx][col] = val;
        setData(newData);
    };

    // Removed .tabs section since Sidebar handles it
    return (
        <div className="data-editor">
            <div className="toolbar">
                <h3>{activeFile.replace('.csv', '').replace('_', ' ').toUpperCase()}</h3>
                <div className="actions">
                    <button onClick={() => fetchData(activeFile)} className="icon-btn">
                        <RefreshCw size={18} />
                    </button>
                    <button onClick={handleSave} className="primary-btn" disabled={saving}>
                        <Save size={18} />
                        {saving ? text.saving : text.save}
                    </button>
                </div>
            </div>

            <div className="table-container">
                {loading ? (
                    <div className="loading">{text.loading}</div>
                ) : (
                    <table>
                        <thead>
                            <tr>
                                {headers.map((h, i) => <th key={i}>{h}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {data.map((row, rIdx) => (
                                <tr key={rIdx}>
                                    {headers.map((col, cIdx) => (
                                        <td key={cIdx}>
                                            <input
                                                value={row[col] || ''}
                                                onChange={(e) => handleChange(rIdx, col, e.target.value)}
                                            />
                                        </td>
                                    ))}
                                </tr>
                            ))}
                            {data.length === 0 && <tr><td colSpan="100%" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>{text.dataEditorEmpty} {activeFile}</td></tr>}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default DataEditor;
