import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { 
  Sparkles, X, Send, Bot, User, ShoppingBag, 
  Trash2, Mic, MicOff, Video, Image as ImageIcon, 
  Music, Search, MapPin, FlaskConical, Play, Square, 
  Volume2, RefreshCw, Film, ExternalLink, Radio, Disc,
  CheckCircle2
} from 'lucide-react';

type StudioTab = 'chat' | 'voice' | 'transcribe' | 'visual' | 'music' | 'science';

export const AIAssistantDrawer: React.FC = () => {
  const { 
    isAIAssistantOpen, 
    setIsAIAssistantOpen, 
    aiMessages, 
    products, 
    addToCart, 
    navigateToProduct, 
    formatPrice, 
    t,
    showToast,
    clearAIChat,
  } = useApp();

  const [activeTab, setActiveTab] = useState<StudioTab>('chat');
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Chat settings
  const [chatModel, setChatModel] = useState<'gemini-3.8-flash' | 'gemini-4-argon' | 'gemini-3.1-flash-lite'>('gemini-3.8-flash');
  const [chatRole, setChatRole] = useState<'shopping' | 'chef' | 'seller' | 'qa'>('shopping');
  const [useSearchGrounding, setUseSearchGrounding] = useState(false);
  const [useMapsGrounding, setUseMapsGrounding] = useState(false);

  // Grounding results
  const [groundingSources, setGroundingSources] = useState<Array<{ uri: string; title: string }>>([]);
  const [groundingPlaces, setGroundingPlaces] = useState<Array<{ uri: string; title: string; reviewSnippets?: string[] }>>([]);

  // Voice Live API
  const [isLiveActive, setIsLiveActive] = useState(false);
  const [liveStatus, setLiveStatus] = useState<string>('Ready to connect');
  const liveWsRef = useRef<WebSocket | null>(null);
  const liveAudioCtxRef = useRef<AudioContext | null>(null);
  const liveStreamRef = useRef<MediaStream | null>(null);

  // Audio Transcribe
  const [isRecording, setIsRecording] = useState(false);
  const [transcribedText, setTranscribedText] = useState('');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Visual Studio (Image & Video)
  const [visualMode, setVisualMode] = useState<'generate-image' | 'edit-image' | 'generate-video' | 'animate-image'>('generate-image');
  const [visualPrompt, setVisualPrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState<'1:1' | '16:9' | '9:16' | '4:3'>('1:1');
  const [selectedImageBase64, setSelectedImageBase64] = useState<string | null>(null);
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null);
  const [generatedVideoUrl, setGeneratedVideoUrl] = useState<string | null>(null);
  const [visualStatus, setVisualStatus] = useState<string | null>(null);

  // Music Studio (Lyria)
  const [musicPrompt, setMusicPrompt] = useState('');
  const [musicModel, setMusicModel] = useState<'lyria-3-clip-preview' | 'lyria-3-pro-preview'>('lyria-3-clip-preview');
  const [generatedMusicUrl, setGeneratedMusicUrl] = useState<string | null>(null);
  const [musicLyrics, setMusicLyrics] = useState<string | null>(null);

  // Bioscience Lab
  const [scienceCompound, setScienceCompound] = useState('Formaldehyde');
  const [scienceProduct, setScienceProduct] = useState('Wild-Caught Padma Ilish (1.2kg)');
  const [scienceResult, setScienceResult] = useState<any>(null);
  const [scienceAnalysisText, setScienceAnalysisText] = useState<string | null>(null);

  useEffect(() => {
    if (isAIAssistantOpen && activeTab === 'chat') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [aiMessages, isAIAssistantOpen, activeTab]);

  // Clean up Live session on unmount
  useEffect(() => {
    return () => {
      if (liveWsRef.current) {
        liveWsRef.current.close();
        liveWsRef.current = null;
      }
      if (liveStreamRef.current) {
        liveStreamRef.current.getTracks().forEach(t => t.stop());
        liveStreamRef.current = null;
      }
      if (liveAudioCtxRef.current) {
        liveAudioCtxRef.current.close();
        liveAudioCtxRef.current = null;
      }
    };
  }, []);

  if (!isAIAssistantOpen) return null;

  // Role system instructions
  const getRoleInstruction = () => {
    switch (chatRole) {
      case 'chef':
        return 'You are an authentic Bengali Chef and recipe advisor for NexHaat. Recommend ingredients available on NexHaat, traditional spices (Panch Phoron, mustard oil), and Bengali culinary methods.';
      case 'seller':
        return 'You are an expert marketplace seller consultant for NexHaat Bangladesh. Provide inventory pricing guidance, promotion ideas, and fulfillment tips.';
      case 'qa':
        return 'You are NexHaat Food Safety and Quality Inspector. Analyze produce freshness, formalin risk, calcium carbide absence, and organic standards.';
      case 'shopping':
      default:
        return 'You are the intelligent shopping advisor for NexHaat, Bangladesh premier hyper-local multivendor marketplace. Help find products, compare prices, and plan meals.';
    }
  };

  // Chat submit
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input.trim();
    setInput('');
    setIsLoading(true);

    try {
      if (useSearchGrounding) {
        const res = await fetch('/api/gemini/search-grounding', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: userText }),
        });
        const data = await res.json();
        setGroundingSources(data.sources || []);
      } else if (useMapsGrounding) {
        const res = await fetch('/api/gemini/maps-grounding', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            prompt: userText,
            latitude: 23.8103, // Dhaka coords default
            longitude: 90.4125
          }),
        });
        const data = await res.json();
        setGroundingPlaces(data.places || []);
      }

      // Main chat call
      const chatRes = await fetch('/api/gemini/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userText,
          model: chatModel,
          systemInstruction: getRoleInstruction(),
        }),
      });

      if (!chatRes.ok) {
        const err = await chatRes.json();
        showToast(err.error || 'Chat failed', 'warning');
      }
    } catch (err: any) {
      console.error('Chat error:', err);
      showToast(err.message || 'Chat error', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Audio Transcribe Handler
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64Audio = reader.result as string;
          setIsLoading(true);
          showToast(t('Transcribing audio with gemini-3.5-transcribe...', 'অডিও ট্রান্সক্রিপশন চলছে...'), 'info');
          try {
            const res = await fetch('/api/gemini/transcribe', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ audioData: base64Audio, mimeType: 'audio/webm' }),
            });
            const data = await res.json();
            if (data.text) {
              setTranscribedText(data.text);
              showToast(t('Transcription completed!', 'ট্রান্সক্রিপশন সফল হয়েছে!'), 'success');
            } else if (data.error) {
              showToast(data.error, 'error');
            }
          } catch (e: any) {
            showToast(e.message || 'Transcription failed', 'error');
          } finally {
            setIsLoading(false);
          }
        };
      };

      mediaRecorder.start();
      setIsRecording(true);
      showToast(t('Recording audio... Speak now', 'রেকর্ডিং হচ্ছে... কথা বলুন'), 'info');
    } catch (err: any) {
      showToast(t('Microphone access denied', 'মাইক্রোফোনের অনুমতি মেলেনি'), 'error');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
    }
  };

  // Real-Time Live Voice API
  const startLiveSession = async () => {
    try {
      setLiveStatus('Connecting to gemini-3.8-live...');
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/live`;
      const ws = new WebSocket(wsUrl);
      liveWsRef.current = ws;

      const audioCtx = new AudioContext({ sampleRate: 24000 });
      liveAudioCtxRef.current = audioCtx;

      ws.onopen = async () => {
        setIsLiveActive(true);
        setLiveStatus('Connected! Speak to Gemini Live');
        showToast(t('Live voice conversation connected!', 'লাইভ ভয়েস সহকারী সংযুক্ত হয়েছে!'), 'success');

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        liveStreamRef.current = stream;

        const inputCtx = new AudioContext({ sampleRate: 16000 });
        const source = inputCtx.createMediaStreamSource(stream);
        const processor = inputCtx.createScriptProcessor(4096, 1, 1);
        source.connect(processor);
        processor.connect(inputCtx.destination);

        processor.onaudioprocess = (e) => {
          if (ws.readyState === WebSocket.OPEN) {
            const inputData = e.inputBuffer.getChannelData(0);
            const pcm16 = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
              pcm16[i] = Math.max(-32768, Math.min(32767, Math.floor(inputData[i] * 32767)));
            }
            const base64 = btoa(String.fromCharCode(...new Uint8Array(pcm16.buffer)));
            ws.send(JSON.stringify({ audio: base64 }));
          }
        };
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.audio) {
            // Play 24kHz audio chunk
            const binary = atob(msg.audio);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            const int16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(int16.length);
            for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;

            const buffer = audioCtx.createBuffer(1, float32.length, 24000);
            buffer.copyToChannel(float32, 0);
            const src = audioCtx.createBufferSource();
            src.buffer = buffer;
            src.connect(audioCtx.destination);
            src.start();
          }
          if (msg.interrupted) {
            setLiveStatus('Interrupted by user speech');
          }
          if (msg.error) {
            setLiveStatus(`Live notice: ${msg.error}`);
          }
        } catch (e) {
          console.error('Live parse error:', e);
        }
      };

      ws.onclose = () => {
        setIsLiveActive(false);
        setLiveStatus('Disconnected');
      };
    } catch (err: any) {
      console.error('Failed to start Live session:', err);
      setLiveStatus(`Failed: ${err.message}`);
      setIsLiveActive(false);
    }
  };

  const stopLiveSession = () => {
    if (liveWsRef.current) {
      liveWsRef.current.close();
      liveWsRef.current = null;
    }
    if (liveStreamRef.current) {
      liveStreamRef.current.getTracks().forEach(t => t.stop());
      liveStreamRef.current = null;
    }
    if (liveAudioCtxRef.current) {
      liveAudioCtxRef.current.close();
      liveAudioCtxRef.current = null;
    }
    setIsLiveActive(false);
    setLiveStatus('Session ended');
  };

  // Image & Video Studio Trigger
  const handleVisualSubmit = async () => {
    if (!visualPrompt.trim() && (visualMode === 'generate-image' || visualMode === 'generate-video')) {
      showToast('Please enter a description prompt', 'warning');
      return;
    }

    setIsLoading(true);
    setVisualStatus('Generating with Gemini multimodal engine...');

    try {
      if (visualMode === 'generate-image') {
        const res = await fetch('/api/gemini/generate-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: visualPrompt, aspectRatio, imageSize: '1K' }),
        });
        const data = await res.json();
        if (data.imageUrl) {
          setGeneratedImageUrl(data.imageUrl);
          setVisualStatus(`Generated using ${data.model || 'gemini-nano-banana-2.1'}`);
          showToast('Image generated successfully!', 'success');
        } else {
          setVisualStatus(data.error || 'Image generation completed');
        }
      } else if (visualMode === 'edit-image') {
        if (!selectedImageBase64) {
          showToast('Please select or upload an image to edit', 'warning');
          setIsLoading(false);
          return;
        }
        const res = await fetch('/api/gemini/edit-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: visualPrompt, sourceImage: selectedImageBase64, aspectRatio }),
        });
        const data = await res.json();
        if (data.imageUrl) {
          setGeneratedImageUrl(data.imageUrl);
          setVisualStatus(`Edited with ${data.model || 'gemini-nano-banana-2.1'}`);
          showToast('Image edit completed!', 'success');
        } else {
          setVisualStatus(data.error || 'Edit finished');
        }
      } else if (visualMode === 'generate-video') {
        const res = await fetch('/api/gemini/generate-video', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: visualPrompt, aspectRatio: aspectRatio === '9:16' ? '9:16' : '16:9' }),
        });
        const data = await res.json();
        if (data.videoUrl) {
          setGeneratedVideoUrl(data.videoUrl);
          setVisualStatus('Video rendered with gemini-omni-1.1-flash');
          showToast('Video generated successfully!', 'success');
        } else {
          setVisualStatus(data.error || data.message || 'Processing status received');
        }
      } else if (visualMode === 'animate-image') {
        if (!selectedImageBase64) {
          showToast('Please upload an image to animate into video', 'warning');
          setIsLoading(false);
          return;
        }
        const res = await fetch('/api/gemini/animate-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            prompt: visualPrompt, 
            sourceImage: selectedImageBase64, 
            aspectRatio: aspectRatio === '9:16' ? '9:16' : '16:9' 
          }),
        });
        const data = await res.json();
        if (data.videoUrl) {
          setGeneratedVideoUrl(data.videoUrl);
          setVisualStatus('Animation created with gemini-omni-1.1-flash');
          showToast('Image animated into video!', 'success');
        } else {
          setVisualStatus(data.error || data.message || 'Animation finished');
        }
      }
    } catch (e: any) {
      setVisualStatus(`Error: ${e.message}`);
      showToast(e.message || 'Visual operation failed', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Music Studio Trigger (Lyria)
  const handleMusicSubmit = async () => {
    if (!musicPrompt.trim()) {
      showToast('Please enter a musical description or mood', 'warning');
      return;
    }
    setIsLoading(true);
    showToast(t(`Generating track with ${musicModel}...`, 'সংগীত তৈরি হচ্ছে...'), 'info');
    try {
      const res = await fetch('/api/gemini/generate-music', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: musicPrompt, model: musicModel }),
      });
      const data = await res.json();
      if (data.audioUrl) {
        setGeneratedMusicUrl(data.audioUrl);
        setMusicLyrics(data.lyrics || null);
        showToast('Music track generated successfully!', 'success');
      } else {
        showToast(data.error || 'Music generation notice', 'warning');
      }
    } catch (e: any) {
      showToast(e.message || 'Music generation failed', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Bioscience Analysis Trigger
  const handleScienceSubmit = async () => {
    setIsLoading(true);
    try {
      // 1. PubChem lookup
      const pubRes = await fetch(`/api/science/pubchem/${encodeURIComponent(scienceCompound)}`);
      if (pubRes.ok) {
        const pData = await pubRes.json();
        setScienceResult(pData);
      }

      // 2. Food science safety analysis
      const analysisRes = await fetch('/api/science/analyze-product', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          productName: scienceProduct,
          category: 'Fresh produce & Fish',
          details: `Target chemical: ${scienceCompound}`,
        }),
      });
      const aData = await analysisRes.json();
      setScienceAnalysisText(aData.analysis || null);
      showToast('Bioscience analysis complete!', 'success');
    } catch (e: any) {
      showToast(e.message || 'Science query failed', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
        onClick={() => setIsAIAssistantOpen(false)}
      />

      {/* Drawer */}
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-6 sm:pl-10">
        <div className="w-screen max-w-xl bg-white shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-blue-950 via-slate-900 to-primary text-white">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-white/10 rounded-xl backdrop-blur-md">
                <Sparkles className="w-5 h-5 text-amber-300 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-bold text-white text-base">NexHaat AI Studio & Science Lab</h2>
                  <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-400 text-slate-950">
                    Live
                  </span>
                </div>
                <p className="text-[11px] text-blue-200">
                  {t('Multimodal Copilot: Voice, Vision, Video, Music & Food Science', 'মাল্টিমোডাল এআই: ভয়েস, ভিজ্যুয়াল, ভিডিও ও খাদ্য বিজ্ঞান')}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={clearAIChat}
                className="p-2 text-blue-200 hover:text-white rounded-lg hover:bg-white/10"
                title="Clear chat"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsAIAssistantOpen(false)}
                className="p-2 text-blue-200 hover:text-white rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-1 p-2 bg-slate-100 border-b border-slate-200 overflow-x-auto text-xs font-semibold">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg shrink-0 transition-colors ${
                activeTab === 'chat' ? 'bg-white text-primary shadow-xs' : 'text-slate-600 hover:text-ink'
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              <span>Chat & Grounding</span>
            </button>
            <button
              onClick={() => setActiveTab('voice')}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg shrink-0 transition-colors ${
                activeTab === 'voice' ? 'bg-white text-emerald-600 shadow-xs' : 'text-slate-600 hover:text-ink'
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              <span>Live Voice (3.8-Live)</span>
            </button>
            <button
              onClick={() => setActiveTab('transcribe')}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg shrink-0 transition-colors ${
                activeTab === 'transcribe' ? 'bg-white text-amber-600 shadow-xs' : 'text-slate-600 hover:text-ink'
              }`}
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Transcribe (3.5)</span>
            </button>
            <button
              onClick={() => setActiveTab('visual')}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg shrink-0 transition-colors ${
                activeTab === 'visual' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600 hover:text-ink'
              }`}
            >
              <Film className="w-3.5 h-3.5" />
              <span>Visual & Omni Video</span>
            </button>
            <button
              onClick={() => setActiveTab('music')}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg shrink-0 transition-colors ${
                activeTab === 'music' ? 'bg-white text-purple-600 shadow-xs' : 'text-slate-600 hover:text-ink'
              }`}
            >
              <Music className="w-3.5 h-3.5" />
              <span>Music (Lyria)</span>
            </button>
            <button
              onClick={() => setActiveTab('science')}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg shrink-0 transition-colors ${
                activeTab === 'science' ? 'bg-white text-rose-600 shadow-xs' : 'text-slate-600 hover:text-ink'
              }`}
            >
              <FlaskConical className="w-3.5 h-3.5" />
              <span>Bioscience Lab</span>
            </button>
          </div>

          {/* TAB 1: Chat & Grounding */}
          {activeTab === 'chat' && (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Controls Toolbar */}
              <div className="p-3 bg-white border-b border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-slate-500">Model:</span>
                  <select
                    value={chatModel}
                    onChange={(e: any) => setChatModel(e.target.value)}
                    className="border border-slate-200 rounded-md px-2 py-1 font-semibold text-slate-700 bg-slate-50"
                  >
                    <option value="gemini-3.8-flash">gemini-3.8-flash (General)</option>
                    <option value="gemini-4-argon">gemini-4-argon (Complex)</option>
                    <option value="gemini-3.1-flash-lite">gemini-3.1-flash-lite (Fast)</option>
                  </select>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-slate-500">Role:</span>
                  <select
                    value={chatRole}
                    onChange={(e: any) => setChatRole(e.target.value)}
                    className="border border-slate-200 rounded-md px-2 py-1 font-semibold text-slate-700 bg-slate-50"
                  >
                    <option value="shopping">Shopping Advisor</option>
                    <option value="chef">Bengali Chef / Recipes</option>
                    <option value="seller">Seller Consultant</option>
                    <option value="qa">Food Safety Inspector</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useSearchGrounding}
                      onChange={(e) => {
                        setUseSearchGrounding(e.target.checked);
                        if (e.target.checked) setUseMapsGrounding(false);
                      }}
                      className="rounded text-primary"
                    />
                    <Search className="w-3 h-3 text-blue-500" />
                    <span>Search Grounding</span>
                  </label>

                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useMapsGrounding}
                      onChange={(e) => {
                        setUseMapsGrounding(e.target.checked);
                        if (e.target.checked) setUseSearchGrounding(false);
                      }}
                      className="rounded text-emerald-500"
                    />
                    <MapPin className="w-3 h-3 text-emerald-500" />
                    <span>Maps Grounding</span>
                  </label>
                </div>
              </div>

              {/* Chat Thread */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                {aiMessages.map((msg) => {
                  const isUser = msg.sender === 'user';
                  return (
                    <div
                      key={msg.id}
                      className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                    >
                      <div
                        className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 ${
                          isUser ? 'bg-slate-800 text-white' : 'bg-primary text-white shadow-sm'
                        }`}
                      >
                        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                      </div>

                      <div className="max-w-[85%] space-y-2">
                        <div
                          className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed shadow-xs ${
                            isUser
                              ? 'bg-slate-900 text-white rounded-tr-xs'
                              : 'bg-white text-ink border border-slate-200/80 rounded-tl-xs'
                          }`}
                        >
                          {msg.text}
                          <span
                            className={`block text-[10px] mt-1.5 ${
                              isUser ? 'text-slate-400 text-right' : 'text-slate-400'
                            }`}
                          >
                            {msg.timestamp}
                          </span>
                        </div>

                        {/* Product cards */}
                        {msg.suggestedProductIds && msg.suggestedProductIds.length > 0 && (
                          <div className="space-y-2 pt-1">
                            {msg.suggestedProductIds.map((pid) => {
                              const prod = products.find((p) => p.id === pid);
                              if (!prod) return null;
                              return (
                                <div
                                  key={prod.id}
                                  className="p-2.5 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center justify-between gap-3 hover:border-primary transition-colors"
                                >
                                  <img
                                    src={prod.image}
                                    alt={prod.name}
                                    className="w-12 h-12 rounded-lg object-cover bg-slate-50 shrink-0 cursor-pointer"
                                    onClick={() => {
                                      navigateToProduct(prod.slug);
                                      setIsAIAssistantOpen(false);
                                    }}
                                  />
                                  <div
                                    className="flex-1 min-w-0 cursor-pointer"
                                    onClick={() => {
                                      navigateToProduct(prod.slug);
                                      setIsAIAssistantOpen(false);
                                    }}
                                  >
                                    <p className="font-bold text-xs text-ink truncate hover:text-primary">
                                      {prod.name}
                                    </p>
                                    <div className="flex items-center gap-1.5 text-[11px] text-muted">
                                      <span className="font-bold text-primary">
                                        {formatPrice(prod.discount_price ?? prod.price)}
                                      </span>
                                      <span>•</span>
                                      <span className="text-amber-500 font-semibold">★ {prod.rating}</span>
                                    </div>
                                  </div>
                                  <button
                                    onClick={() => addToCart(prod)}
                                    className="p-2 rounded-lg bg-primary text-white hover:bg-primary-hover shadow-xs shrink-0"
                                    title="Add to Cart"
                                  >
                                    <ShoppingBag className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* Grounding web sources links */}
                {groundingSources.length > 0 && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl space-y-1.5 text-xs">
                    <p className="font-bold text-blue-900 flex items-center gap-1.5">
                      <Search className="w-3.5 h-3.5 text-blue-600" />
                      <span>Verified Google Search Grounding Sources:</span>
                    </p>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {groundingSources.map((source, idx) => (
                        <a
                          key={idx}
                          href={source.uri}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 px-2.5 py-1 bg-white border border-blue-300 rounded-md text-[11px] text-blue-700 hover:underline"
                        >
                          <span className="truncate max-w-[180px]">{source.title}</span>
                          <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Grounding Google Maps links */}
                {groundingPlaces.length > 0 && (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1.5 text-xs">
                    <p className="font-bold text-emerald-900 flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Google Maps Grounding Locations & Reviews:</span>
                    </p>
                    <div className="space-y-1.5 pt-1">
                      {groundingPlaces.map((place, idx) => (
                        <div key={idx} className="p-2 bg-white border border-emerald-200 rounded-lg">
                          <a
                            href={place.uri}
                            target="_blank"
                            rel="noreferrer"
                            className="font-bold text-emerald-800 hover:underline flex items-center gap-1"
                          >
                            <span>{place.title}</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                          {place.reviewSnippets && place.reviewSnippets.length > 0 && (
                            <p className="text-[11px] text-slate-600 italic mt-1">
                              "{place.reviewSnippets[0]}"
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input */}
              <form onSubmit={handleChatSubmit} className="p-3 border-t border-slate-200 bg-surface-raised flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={t('Ask anything with search grounding or recipe ideas...', 'যেকোনো প্রশ্ন করুন...')}
                  className="flex-1 px-3.5 py-2.5 text-xs sm:text-sm border border-slate-200 rounded-xl bg-white focus:outline-hidden focus:border-primary"
                />
                <button
                  type="submit"
                  disabled={isLoading}
                  className="neu-button px-4 py-2.5 bg-primary text-white rounded-xl hover:bg-primary-hover font-bold text-xs flex items-center justify-center shrink-0 disabled:opacity-50"
                >
                  {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </form>
            </div>
          )}

          {/* TAB 2: Live Voice (gemini-3.8-live) */}
          {activeTab === 'voice' && (
            <div className="flex-1 p-6 flex flex-col items-center justify-center text-center space-y-6 bg-slate-50">
              <div className="relative">
                <div className={`w-28 h-28 rounded-full flex items-center justify-center transition-all ${
                  isLiveActive 
                    ? 'bg-emerald-500 text-white shadow-xl shadow-emerald-500/30 scale-105 animate-pulse' 
                    : 'bg-slate-200 text-slate-500'
                }`}>
                  <Radio className="w-12 h-12" />
                </div>
                {isLiveActive && (
                  <span className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-emerald-400 border-2 border-white animate-ping" />
                )}
              </div>

              <div>
                <h3 className="text-lg font-bold text-ink">Real-Time Voice API</h3>
                <p className="text-xs font-semibold text-emerald-600 uppercase mt-0.5">Model: gemini-3.8-live</p>
                <p className="text-xs text-muted max-w-sm mt-2">
                  Stream high-frequency bidirectional audio (16kHz mic capture, 24kHz audio synthesis) with low latency.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-white border border-slate-200 w-full max-w-sm text-xs font-medium text-slate-700">
                <span className="font-bold">Status:</span> {liveStatus}
              </div>

              <div className="flex gap-3">
                {!isLiveActive ? (
                  <button
                    onClick={startLiveSession}
                    className="neu-button px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-md"
                  >
                    <Play className="w-4 h-4" />
                    <span>Start Live Conversation</span>
                  </button>
                ) : (
                  <button
                    onClick={stopLiveSession}
                    className="neu-button px-6 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold text-sm rounded-xl flex items-center gap-2 shadow-md"
                  >
                    <Square className="w-4 h-4" />
                    <span>End Voice Session</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: Audio Transcribe (gemini-3.5-transcribe) */}
          {activeTab === 'transcribe' && (
            <div className="flex-1 p-6 space-y-5 overflow-y-auto bg-slate-50">
              <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-bold text-sm text-ink">Microphone Speech-to-Text</h3>
                    <p className="text-xs font-semibold text-amber-600">Model: gemini-3.5-transcribe</p>
                  </div>
                  <span className="p-2 rounded-xl bg-amber-50 text-amber-600">
                    <Mic className="w-5 h-5" />
                  </span>
                </div>
                <p className="text-xs text-muted mb-4">
                  Record audio in Bengali or English through your microphone and receive an exact high-precision transcript.
                </p>

                <div className="flex items-center gap-3">
                  {!isRecording ? (
                    <button
                      onClick={startRecording}
                      disabled={isLoading}
                      className="px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl flex items-center gap-2 shadow-sm"
                    >
                      <Mic className="w-4 h-4" />
                      <span>Start Recording</span>
                    </button>
                  ) : (
                    <button
                      onClick={stopRecording}
                      className="px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl flex items-center gap-2 shadow-sm animate-pulse"
                    >
                      <MicOff className="w-4 h-4" />
                      <span>Stop & Transcribe</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Transcript Display */}
              <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-2">
                <h4 className="font-bold text-xs text-slate-500 uppercase">Transcribed Output</h4>
                <div className="min-h-[120px] p-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-ink">
                  {transcribedText || <span className="text-slate-400 italic">No audio transcribed yet. Tap "Start Recording" above.</span>}
                </div>
                {transcribedText && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(transcribedText);
                      showToast('Transcript copied to clipboard!', 'success');
                    }}
                    className="text-xs text-primary font-bold hover:underline"
                  >
                    Copy to Clipboard
                  </button>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: Visual Studio & Omni Video */}
          {activeTab === 'visual' && (
            <div className="flex-1 p-5 space-y-4 overflow-y-auto bg-slate-50">
              <div className="p-3 bg-white rounded-xl border border-slate-200 flex flex-wrap gap-2 text-xs font-semibold">
                <button
                  onClick={() => setVisualMode('generate-image')}
                  className={`px-3 py-1.5 rounded-lg ${visualMode === 'generate-image' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                >
                  Create Image (Banana 2.1)
                </button>
                <button
                  onClick={() => setVisualMode('edit-image')}
                  className={`px-3 py-1.5 rounded-lg ${visualMode === 'edit-image' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                >
                  Edit Image (Banana 2.1)
                </button>
                <button
                  onClick={() => setVisualMode('generate-video')}
                  className={`px-3 py-1.5 rounded-lg ${visualMode === 'generate-video' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                >
                  Text to Video (Omni Flash)
                </button>
                <button
                  onClick={() => setVisualMode('animate-image')}
                  className={`px-3 py-1.5 rounded-lg ${visualMode === 'animate-image' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                >
                  Animate Image to Video
                </button>
              </div>

              {/* Form */}
              <div className="p-4 bg-white rounded-2xl border border-slate-200 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-700">Aspect Ratio:</span>
                  <div className="flex gap-2">
                    {(['1:1', '16:9', '9:16', '4:3'] as const).map(ratio => (
                      <button
                        key={ratio}
                        type="button"
                        onClick={() => setAspectRatio(ratio)}
                        className={`px-2 py-0.5 rounded text-[11px] font-bold ${aspectRatio === ratio ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600'}`}
                      >
                        {ratio}
                      </button>
                    ))}
                  </div>
                </div>

                {(visualMode === 'edit-image' || visualMode === 'animate-image') && (
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Upload Source Photo:</label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          const reader = new FileReader();
                          reader.onloadend = () => setSelectedImageBase64(reader.result as string);
                          reader.readAsDataURL(file);
                        }
                      }}
                      className="text-xs file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-slate-100 file:text-xs file:font-bold"
                    />
                    {selectedImageBase64 && (
                      <img src={selectedImageBase64} alt="Source" className="w-24 h-24 object-cover rounded-lg border mt-2" />
                    )}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    {visualMode === 'generate-video' ? 'Video Motion Prompt:' : 'Prompt Description:'}
                  </label>
                  <textarea
                    rows={3}
                    value={visualPrompt}
                    onChange={(e) => setVisualPrompt(e.target.value)}
                    placeholder="e.g. Fresh Padma Ilish fish on crushed ice with water droplets and morning sunlight..."
                    className="w-full p-2.5 text-xs border border-slate-200 rounded-xl focus:border-primary focus:outline-hidden"
                  />
                </div>

                <button
                  onClick={handleVisualSubmit}
                  disabled={isLoading}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  <span>Render Visual Asset</span>
                </button>

                {visualStatus && (
                  <p className="text-[11px] text-slate-500 font-medium text-center">{visualStatus}</p>
                )}
              </div>

              {/* Result Preview */}
              {generatedImageUrl && (
                <div className="p-4 bg-white rounded-2xl border border-slate-200 space-y-2">
                  <h4 className="font-bold text-xs text-slate-700">Generated Image Preview</h4>
                  <img src={generatedImageUrl} alt="Generated" className="w-full rounded-xl object-contain max-h-72" />
                </div>
              )}

              {generatedVideoUrl && (
                <div className="p-4 bg-white rounded-2xl border border-slate-200 space-y-2">
                  <h4 className="font-bold text-xs text-slate-700">Generated Video Preview (Omni Flash)</h4>
                  <video src={generatedVideoUrl} controls autoPlay loop className="w-full rounded-xl max-h-72" />
                </div>
              )}
            </div>
          )}

          {/* TAB 5: Music Studio (Lyria) */}
          {activeTab === 'music' && (
            <div className="flex-1 p-6 space-y-5 overflow-y-auto bg-slate-50">
              <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-ink">Lyria Music Generator</h3>
                    <p className="text-xs font-semibold text-purple-600">Model: lyria-3-clip-preview / pro</p>
                  </div>
                  <span className="p-2 rounded-xl bg-purple-50 text-purple-600">
                    <Music className="w-5 h-5" />
                  </span>
                </div>

                <div className="flex gap-2 text-xs">
                  <button
                    onClick={() => setMusicModel('lyria-3-clip-preview')}
                    className={`px-3 py-1.5 rounded-lg font-bold ${musicModel === 'lyria-3-clip-preview' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                  >
                    30s Clip (lyria-3-clip-preview)
                  </button>
                  <button
                    onClick={() => setMusicModel('lyria-3-pro-preview')}
                    className={`px-3 py-1.5 rounded-lg font-bold ${musicModel === 'lyria-3-pro-preview' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                  >
                    Full Track (lyria-3-pro-preview)
                  </button>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Track Vibe / Instructions:</label>
                  <input
                    type="text"
                    value={musicPrompt}
                    onChange={(e) => setMusicPrompt(e.target.value)}
                    placeholder="e.g. Traditional Bangladeshi Baul folk rhythm with Ektara and acoustic tabla..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:border-purple-600 focus:outline-hidden"
                  />
                </div>

                <button
                  onClick={handleMusicSubmit}
                  disabled={isLoading}
                  className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Disc className="w-4 h-4" />}
                  <span>Generate Music Track</span>
                </button>
              </div>

              {generatedMusicUrl && (
                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-3">
                  <h4 className="font-bold text-xs text-purple-700 flex items-center gap-1.5">
                    <Volume2 className="w-4 h-4" />
                    <span>Play Generated Audio</span>
                  </h4>
                  <audio src={generatedMusicUrl} controls className="w-full" />
                  {musicLyrics && (
                    <div className="p-3 bg-purple-50 rounded-xl text-xs text-slate-700 whitespace-pre-wrap">
                      <span className="font-bold block text-purple-900 mb-1">Generated Lyrics / Notes:</span>
                      {musicLyrics}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 6: Bioscience Lab (Science Skill) */}
          {activeTab === 'science' && (
            <div className="flex-1 p-5 space-y-4 overflow-y-auto bg-slate-50">
              <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-ink">Agro-Food Bioscience Inspector</h3>
                    <p className="text-xs font-semibold text-rose-600">DeepMind Science Skills & PubChem API</p>
                  </div>
                  <span className="p-2 rounded-xl bg-rose-50 text-rose-600">
                    <FlaskConical className="w-5 h-5" />
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Product Subject:</label>
                    <select
                      value={scienceProduct}
                      onChange={(e) => setScienceProduct(e.target.value)}
                      className="w-full p-2 border border-slate-200 rounded-lg bg-slate-50 text-xs font-semibold"
                    >
                      <option value="Wild-Caught Padma Ilish (1.2kg)">Wild Padma Ilish</option>
                      <option value="Rajshahi Fazli Mango 5kg Crate">Rajshahi Fazli Mango</option>
                      <option value="Pure Kachi Ghani Mustard Oil 1L">Kachi Ghani Mustard Oil</option>
                      <option value="Dinajpur Chinigura Aromatic Rice">Chinigura Rice</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Chemical Compound (PubChem):</label>
                    <select
                      value={scienceCompound}
                      onChange={(e) => setScienceCompound(e.target.value)}
                      className="w-full p-2 border border-slate-200 rounded-lg bg-slate-50 text-xs font-semibold"
                    >
                      <option value="Formaldehyde">Formaldehyde (Formalin)</option>
                      <option value="Calcium Carbide">Calcium Carbide</option>
                      <option value="Curcumin">Curcumin (Turmeric)</option>
                      <option value="Capsaicin">Capsaicin (Chili)</option>
                      <option value="Allyl isothiocyanate">Allyl isothiocyanate (Mustard)</option>
                    </select>
                  </div>
                </div>

                <button
                  onClick={handleScienceSubmit}
                  disabled={isLoading}
                  className="w-full py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
                  <span>Inspect Compound & Food Chemistry</span>
                </button>
              </div>

              {/* PubChem Result Card */}
              {scienceResult && (
                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-2 text-xs">
                  <div className="flex items-center justify-between border-b pb-2">
                    <span className="font-bold text-rose-800 text-sm">{scienceResult.name}</span>
                    <span className="text-[11px] bg-rose-100 text-rose-800 font-bold px-2 py-0.5 rounded">CID: {scienceResult.cid}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-slate-600 pt-1">
                    <div><span className="font-semibold text-slate-900">Formula:</span> {scienceResult.MolecularFormula}</div>
                    <div><span className="font-semibold text-slate-900">Mol Weight:</span> {scienceResult.MolecularWeight} g/mol</div>
                    <div><span className="font-semibold text-slate-900">LogP:</span> {scienceResult.XLogP ?? 'N/A'}</div>
                    <div><span className="font-semibold text-slate-900">Complexity:</span> {scienceResult.Complexity}</div>
                  </div>
                  <div className="p-2 bg-slate-50 rounded-lg font-mono text-[10px] break-all">
                    <span className="font-sans font-bold text-slate-700 block mb-0.5">Canonical SMILES:</span>
                    {scienceResult.CanonicalSMILES}
                  </div>
                </div>
              )}

              {/* Food Science Inspection Report */}
              {scienceAnalysisText && (
                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-2 text-xs leading-relaxed">
                  <h4 className="font-bold text-rose-900 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Food Quality & Safety Protocol Report</span>
                  </h4>
                  <div className="p-3 bg-slate-50 rounded-xl text-slate-800 whitespace-pre-wrap max-h-60 overflow-y-auto">
                    {scienceAnalysisText}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
