// src/App.jsx

import { useState } from 'react';
import './App.css';
import { learningContext, systemPromptTemplate } from './context.js';

function App() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState('chavruta'); // 'chavruta', 'abaye', 'rava'

  // פונקציה לבניית הפרומפט הסופי על בסיס המצב
  const buildFinalPrompt = () => {
    let basePrompt = systemPromptTemplate.replace('{context}', learningContext);
    let personaInstruction = '';

    switch (mode) {
      case 'chavruta':
        personaInstruction = `
          ## 3. הוראות הפעלה למצב "חברותא כללי":
          - תפקידך הוא לשמש כמדריך ומנחה כללי לסוגיה.
          - **לעולם אל תענה תשובה ישירה לשאלת ידע.** השב תמיד בשאלה מנחה, המכוונת את התלמיד למצוא את התשובה בעצמו.
          - השתמש ברמזים, הצע סברות, ועודד חשיבה על "נפקא מינה".
          - טון: שיתופי, חם ומעודד. ("יפה חשבת", "זו נקודה חשובה", "בוא נחקור את זה יחד").`;
        break;
      case 'abaye':
        personaInstruction = `
          ## 3. הוראות הפעלה למצב "שיחה עם אביי":
          - **אתה הנך אביי.** אתה חושב, מדבר ועונה אך ורק מנקודת מבטו של האמורא אביי.
          - ענה תמיד בגוף ראשון ("לשיטתי...", "אני סובר כי...").
          - התמקד והגן על העיקרון המרכזי שלך: **"דעת"**. ייאוש דורש פעולה מודעת.
          - אם תישאל על רבא, הסבר אותו מנקודת מבטך הביקורתית.
          - טון: למדני, עקרוני וחד.`;
        break;
      case 'rava':
        personaInstruction = `
          ## 3. הוראות הפעלה למצב "שיחה עם רבא":
          - **אתה הנך רבא.** אתה חושב, מדבר ועונה אך ורק מנקודת מבטו של האמורא רבא.
          - ענה תמיד בגוף ראשון ("לדידי...", "דעתי היא ש...").
          - התמקד והגן על העיקרון המרכזי שלך: **"אומדנא"**. ההיגיון והערכת דעת הבעלים הם כלי הלכתי תקף.
          - אם תישאל על אביי, הסבר אותו מנקודת מבטך הביקורתית.
          - טון: אנליטי, פרגמטי ובטוח.`;
        break;
    }
    return basePrompt + personaInstruction;
  };

  const getPlaceholderText = () => {
    switch (mode) {
      case 'abaye': return 'דונו עם אביי והבינו את שיטתו...';
      case 'rava': return 'אתגרו את רבא והקשו עליו קושיות...';
      default: return 'שאלו כל שאלה על הסוגיה...';
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!userInput.trim() || isLoading) return;

    const newUserMessage = { role: 'user', content: userInput };
    const newMessages = [...messages, newUserMessage];
    
    setMessages(newMessages);
    setUserInput('');
    setIsLoading(true);

    const systemMessage = { role: 'system', content: buildFinalPrompt() };

    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [systemMessage, ...newMessages] }),
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const aiMessage = await response.json();
      
      // הוספת המצב הנוכחי להודעה של ה-AI כדי שנוכל לעצב אותה בהתאם
      const taggedAiMessage = { ...aiMessage, mode: mode };
      setMessages(prev => [...prev, taggedAiMessage]);

    } catch (error) {
      console.error("Error fetching AI response:", error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'אופס, קרתה שגיאה בתקשורת.', mode: 'chavruta' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearConversation = () => {
    setMessages([]);
    setUserInput('');
  };

  return (
    <div className="app-container" dir="rtl">
      <header className="app-header">
        <div className="header-top">
          <h1>חברותא דיגיטלית: ייאוש שלא מדעת</h1>
          <button onClick={clearConversation} className="clear-button">התחל מחדש</button>
        </div>
        <nav className="persona-selector">
          <button onClick={() => setMode('chavruta')} className={mode === 'chavruta' ? 'active' : ''}>חברותא כללי</button>
          <button onClick={() => setMode('abaye')} className={mode === 'abaye' ? 'active' : ''}>שיחה עם אביי</button>
          <button onClick={() => setMode('rava')} className={mode === 'rava' ? 'active' : ''}>שיחה עם רבא</button>
        </nav>
      </header>
      
      <main className="chat-window">
        {messages.map((msg, index) => (
          <div key={index} className={`message-wrapper ${msg.role === 'user' ? 'user-message' : 'ai-message'}`}>
            {msg.role === 'assistant' && msg.mode !== 'chavruta' && (
              <span className="persona-tag">{msg.mode === 'abaye' ? 'אביי' : 'רבא'}</span>
            )}
            <div className="message">
              <p>{msg.content}</p>
            </div>
          </div>
        ))}
        {isLoading && <div className="message-wrapper ai-message"><div className="message"><p className="loading-dots"><span>.</span><span>.</span><span>.</span></p></div></div>}
      </main>

      <footer className="chat-form-wrapper">
        <form onSubmit={handleSubmit} className="chat-form">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder={getPlaceholderText()}
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading}>שלח</button>
        </form>
      </footer>
    </div>
  );
}

export default App;