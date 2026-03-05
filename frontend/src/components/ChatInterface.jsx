import React, { useState, useRef, useEffect } from 'react';
import { Send, Image as ImageIcon, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { sendChat, getData } from '../api';
import './ChatInterface.css';

const ChatInterface = ({ language }) => {
    const getOnboardingMessage = (lang) => {
        if (lang === 'ru') {
            return (
                "**Привет! Давайте познакомимся.**\n\n" +
                "Я не нашел информации о вас. Расскажите, пожалуйста, о себе:\n" +
                "- Как вас зовут?\n" +
                "- Есть ли у вас аллергии или диетические предпочтения?\n" +
                "- Кто еще живет с вами и какие у них предпочтения в еде?\n\n" +
                "Эта информация поможет мне составлять для вас лучшие планы питания!"
            );
        } else if (lang === 'es') {
            return (
                "**¡Hola! Vamos a conocernos.**\n\n" +
                "No encontré información sobre ti. Por favor cuéntame:\n" +
                "- ¿Cómo te llamas?\n" +
                "- ¿Tienes alergias o preferencias dietéticas?\n" +
                "- ¿Quién más vive contigo y cuáles son sus gustos?\n\n" +
                "¡Esta información me ayudará a crear mejores planes para ti!"
            );
        } else {
            return (
                "**Hello! Let's get to know each other.**\n\n" +
                "I couldn't find any information about you. Please tell me:\n" +
                "- What is your name?\n" +
                "- Do you have any allergies or dietary preferences?\n" +
                "- Who else lives with you and what are their food preferences?\n\n" +
                "This info will help me build better meal plans for you!"
            );
        }
    };

    const getPersonalizedMessage = (lang, name) => {
        if (lang === 'ru') {
            return `**Привет, ${name}!** Рад снова видеть вас.\n\nЧем могу помочь сегодня? Мы можем обновить запасы, спланировать ужин или записать новые привычки.`;
        } else if (lang === 'es') {
            return `**¡Hola, ${name}!** Encantado de verte de nuevo.\n\n¿En qué puedo ayudarte hoy? Podemos actualizar el inventario o planear la cena.`;
        } else {
            return `**Hello, ${name}!** Good to see you again.\n\nHow can I help you today? We can update inventory, plan dinner, or log new habits.`;
        }
    };

    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [image, setImage] = useState(null);
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const [initialized, setInitialized] = useState(false);

    useEffect(() => {
        const initChat = async () => {
            if (initialized) return;

            try {
                const res = await getData('people.csv');
                const people = res.data;
                let msgContent = "";

                if (people && people.length > 0 && people[0].name) {
                    msgContent = getPersonalizedMessage(language, people[0].name);
                } else {
                    msgContent = getOnboardingMessage(language);
                }

                setMessages([{ role: 'assistant', content: msgContent }]);
                setInitialized(true);
            } catch (err) {
                console.error("Failed to fetch people data", err);
                // Fallback to generic if simplified
                setMessages([{ role: 'assistant', content: getOnboardingMessage(language) }]);
                setInitialized(true);
            }
        };

        initChat();
    }, [language, initialized]); // Dependency on language allows refresh if lang changes? 
    // Actually if lang changes, we want to re-fetch or re-render. 
    // Simplified: re-run logic if language changes.
    useEffect(() => {
        setInitialized(false);
    }, [language]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() && !image) return;

        const userMsg = {
            role: 'user',
            content: input,
            image: image ? URL.createObjectURL(image) : null
        };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setImage(null);
        setLoading(true);

        try {
            const formData = new FormData();
            formData.append('message', input || 'Analyzes attached image');
            if (image) {
                formData.append('image', image);
            }

            const res = await sendChat(formData);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: res.data.response,
                logs: res.data.logs || []
            }]);
        } catch (err) {
            console.error(err);
            const errMsg = err.response?.data?.detail || err.message || "Unknown Error";
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `❌ **Error**: ${errMsg}\n\nPlease check server logs.`
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-container">
            <div className="messages">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`message ${msg.role}`}>
                        {msg.image && <img src={msg.image} alt="User upload" className="msg-image" />}
                        <div className="bubble">
                            {msg.logs && msg.logs.length > 0 && (
                                <details className="logs-details">
                                    <summary>Thinking Process ({msg.logs.length} steps)</summary>
                                    <ul>
                                        {msg.logs.map((log, i) => <li key={i}>{log}</li>)}
                                    </ul>
                                </details>
                            )}
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="message assistant">
                        <div className="bubble typing">
                            <Loader2 className="animate-spin" size={16} />
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="input-area">
                {image && (
                    <div className="image-preview">
                        <span>{image.name}</span>
                        <button type="button" onClick={() => setImage(null)}>×</button>
                    </div>
                )}
                <div className="input-wrapper">
                    <label className="icon-btn image-upload">
                        <input
                            type="file"
                            accept="image/*"
                            onChange={(e) => setImage(e.target.files[0])}
                            hidden
                        />
                        <ImageIcon size={20} />
                    </label>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={language === 'ru' ? "Напишите сообщение..." : "Type a message..."}
                    />
                    <button type="submit" className="icon-btn send" disabled={loading || (!input && !image)}>
                        <Send size={20} />
                    </button>
                </div>
            </form>
        </div>
    );
};

export default ChatInterface;
