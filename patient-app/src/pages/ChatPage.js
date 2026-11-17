import React, { useState, useRef, useEffect } from 'react';
import { sendChat } from '../api';

const quickQuestions = {
  en: [
    { icon: '🩹', text: 'How to clean my wound?' },
    { icon: '🔴', text: 'Why is my wound red?' },
    { icon: '💊', text: 'When to change dressing?' },
    { icon: '🚨', text: 'Signs of infection?' },
  ],
  hi: [
    { icon: '🩹', text: 'घाव कैसे साफ करें?' },
    { icon: '🔴', text: 'घाव लाल क्यों है?' },
    { icon: '💊', text: 'ड्रेसिंग कब बदलें?' },
    { icon: '🚨', text: 'संक्रमण के लक्षण?' },
  ],
  od: [
    { icon: '🩹', text: 'ଘା କିପରି ସଫା କରିବେ?' },
    { icon: '🔴', text: 'ଘା ଲାଲ କାହିଁକି?' },
    { icon: '💊', text: 'ଡ୍ରେସିଂ କେବେ ବଦଳାଇବେ?' },
    { icon: '🚨', text: 'ସଂକ୍ରମଣ ଲକ୍�ଣ?' },
  ],
};

const langLabels = { en: '🇬🇧 EN', hi: '🇮🇳 हि', od: '🇮🇳 ଓଡ' };

function ChatPage({ user }) {
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hello! 👋 I\'m your wound care assistant. Ask me anything about post-surgical wound care.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [lang, setLang] = useState('en');
  const endRef = useRef();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async (text) => {
    if (!text.trim()) return;
    const userMsg = { role: 'user', text: text.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    try {
      const res = await sendChat(user.phone, text.trim(), lang);
      setMessages(prev => [...prev, { role: 'bot', text: res.data.reply }]);
    } catch {
      setMessages(prev => [...prev, { role: 'bot', text: 'Sorry, I couldn\'t process that. Please try again.' }]);
    }
    setLoading(false);
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)',
      maxWidth: '480px', margin: '0 auto'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid #E8E7F0',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: '#fff', animation: 'fadeIn 0.3s ease'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '14px',
            background: 'linear-gradient(135deg, #2F2B6E, #7F79B6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '20px'
          }}>🤖</div>
          <div>
            <p style={{ fontWeight: 700, fontSize: '15px', color: '#2F2B6E' }}>WoundCare Bot</p>
            <p style={{ fontSize: '11px', color: '#2BA84A', fontWeight: 600 }}>● Online</p>
          </div>
        </div>

        {/* Language Selector */}
        <div style={{ display: 'flex', gap: '4px', background: '#F5F4FA', borderRadius: '10px', padding: '3px' }}>
          {Object.entries(langLabels).map(([key, label]) => (
            <button key={key} onClick={() => setLang(key)} style={{
              padding: '6px 10px', fontSize: '11px', fontWeight: 600,
              borderRadius: '8px', border: 'none', cursor: 'pointer',
              background: lang === key ? '#2F2B6E' : 'transparent',
              color: lang === key ? '#fff' : '#8C8AAE',
              transition: 'all 0.2s ease'
            }}>{label}</button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '20px',
        display: 'flex', flexDirection: 'column', gap: '12px'
      }}>
        {messages.map((m, i) => (
          <div key={i} style={{
            display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
            animation: 'fadeInUp 0.3s ease forwards'
          }}>
            {m.role === 'bot' && (
              <div style={{
                width: '28px', height: '28px', borderRadius: '10px', flexShrink: 0,
                background: 'linear-gradient(135deg, #EEEDFA, #F5F4FA)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '14px', marginRight: '8px', marginTop: '2px'
              }}>🤖</div>
            )}
            <div style={{
              maxWidth: '78%', padding: '12px 16px', borderRadius: '18px',
              background: m.role === 'user'
                ? 'linear-gradient(135deg, #2F2B6E, #7F79B6)'
                : '#fff',
              color: m.role === 'user' ? '#fff' : '#333',
              fontSize: '14px', lineHeight: '1.55',
              boxShadow: m.role === 'bot' ? '0 2px 8px rgba(47,43,110,0.06)' : 'none',
              borderBottomRightRadius: m.role === 'user' ? '6px' : '18px',
              borderBottomLeftRadius: m.role === 'bot' ? '6px' : '18px'
            }}>
              {m.text}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', animation: 'fadeIn 0.3s ease' }}>
            <div style={{
              width: '28px', height: '28px', borderRadius: '10px',
              background: 'linear-gradient(135deg, #EEEDFA, #F5F4FA)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '14px'
            }}>🤖</div>
            <div style={{
              background: '#fff', padding: '12px 18px', borderRadius: '18px',
              borderBottomLeftRadius: '6px', display: 'flex', gap: '4px',
              boxShadow: '0 2px 8px rgba(47,43,110,0.06)'
            }}>
              {[0, 1, 2].map(d => (
                <div key={d} style={{
                  width: '7px', height: '7px', borderRadius: '50%',
                  background: '#7F79B6', animation: `typing 1.2s ${d * 0.2}s infinite`
                }} />
              ))}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Quick Questions */}
      {messages.length <= 2 && (
        <div style={{
          padding: '0 20px 10px', display: 'flex', gap: '8px', flexWrap: 'wrap',
          animation: 'fadeInUp 0.4s ease forwards'
        }}>
          {quickQuestions[lang].map(q => (
            <button key={q.text} onClick={() => send(q.text)} style={{
              padding: '8px 14px', borderRadius: '20px', fontSize: '12px',
              background: '#fff', color: '#2F2B6E', fontWeight: 600,
              border: '1.5px solid #E8E7F0', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '5px',
              transition: 'all 0.2s ease', whiteSpace: 'nowrap'
            }}>
              <span>{q.icon}</span> {q.text}
            </button>
          ))}
        </div>
      )}

      {/* Input Bar */}
      <div style={{
        padding: '12px 16px', borderTop: '1px solid #E8E7F0',
        background: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(10px)',
        display: 'flex', gap: '10px', alignItems: 'center'
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send(input)}
          placeholder={lang === 'hi' ? 'अपना प्रश्न लिखें...' : lang === 'od' ? 'ଆପଣଙ୍କ ପ୍ରଶ୍ନ ଲେଖନ୍ତୁ...' : 'Ask about wound care...'}
          disabled={loading}
          style={{
            flex: 1, padding: '12px 16px', borderRadius: '24px',
            border: '2px solid #E8E7F0', fontSize: '14px',
            background: '#F7F6FB', height: '48px'
          }}
        />
        <button onClick={() => send(input)} disabled={!input.trim() || loading} style={{
          width: '48px', height: '48px', borderRadius: '50%',
          background: input.trim()
            ? 'linear-gradient(135deg, #2F2B6E, #7F79B6)'
            : '#E8E7F0',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '18px', padding: 0, flexShrink: 0,
          boxShadow: input.trim() ? '0 4px 12px rgba(47,43,110,0.25)' : 'none'
        }}>
          ➤
        </button>
      </div>
    </div>
  );
}

export default ChatPage;
