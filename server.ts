import express, { Request, Response } from 'express';
import cors from 'cors';
import http from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import path from 'path';
import { fileURLToPath } from 'url';
import { GoogleGenAI, Modality, Type } from '@google/genai';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const server = http.createServer(app);

app.use(cors());
app.use(express.json({ limit: '50mb' }));

// Shared server-side Gemini client with telemetry header
const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
  httpOptions: {
    headers: {
      'User-Agent': 'aistudio-build',
    },
  },
});

// 1. Multi-turn Gemini Chat with selectable models and system instructions
app.post('/api/gemini/chat', async (req: Request, res: Response) => {
  try {
    const { 
      messages, 
      prompt, 
      model = 'gemini-3.8-flash', 
      systemInstruction = 'You are the intelligent shopping advisor and customer care assistant for NexHaat, Bangladesh premier hyper-local multivendor marketplace.' 
    } = req.body;

    // Use requested model (gemini-4-argon for complex, gemini-3.8-flash for general, gemini-3.1-flash-lite for fast)
    let selectedModel = model;
    
    // Build conversation history
    const contents: any[] = [];
    if (Array.isArray(messages)) {
      for (const m of messages) {
        contents.push({
          role: m.sender === 'user' ? 'user' : 'model',
          parts: [{ text: m.text }],
        });
      }
    }
    if (prompt) {
      contents.push({
        role: 'user',
        parts: [{ text: prompt }],
      });
    }

    try {
      const response = await ai.models.generateContent({
        model: selectedModel,
        contents,
        config: {
          systemInstruction,
        },
      });

      return res.json({
        text: response.text ?? '',
        model: selectedModel,
      });
    } catch (modelError: any) {
      // If paid model (e.g. gemini-4-argon) fails due to quota or permissions, fallback to gemini-3.8-flash
      if (selectedModel !== 'gemini-3.8-flash') {
        console.warn(`Model ${selectedModel} failed, falling back to gemini-3.8-flash:`, modelError.message);
        const fallbackResponse = await ai.models.generateContent({
          model: 'gemini-3.8-flash',
          contents,
          config: { systemInstruction },
        });
        return res.json({
          text: fallbackResponse.text ?? '',
          model: 'gemini-3.8-flash',
          note: `Auto-switched from ${selectedModel} to gemini-3.8-flash (${modelError.message})`,
        });
      }
      throw modelError;
    }
  } catch (error: any) {
    console.error('Chat error:', error);
    return res.status(500).json({ error: error.message || 'Chat generation failed' });
  }
});

// 2. Google Search Grounding with gemini-3.8-flash
app.post('/api/gemini/search-grounding', async (req: Request, res: Response) => {
  try {
    const { prompt } = req.body;
    if (!prompt) return res.status(400).json({ error: 'Prompt is required' });

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
      },
    });

    const webSources: Array<{ uri: string; title: string }> = [];
    const chunks = response.candidates?.[0]?.groundingMetadata?.groundingChunks;
    if (chunks) {
      for (const chunk of chunks as any[]) {
        if (chunk.web?.uri) {
          webSources.push({
            uri: chunk.web.uri,
            title: chunk.web.title || chunk.web.uri,
          });
        }
      }
    }

    return res.json({
      text: response.text ?? '',
      sources: webSources,
    });
  } catch (error: any) {
    console.error('Search grounding error:', error);
    return res.status(500).json({ error: error.message || 'Search grounding failed' });
  }
});

// 3. Google Maps Grounding with gemini-3.8-flash
app.post('/api/gemini/maps-grounding', async (req: Request, res: Response) => {
  try {
    const { prompt, latitude, longitude } = req.body;
    if (!prompt) return res.status(400).json({ error: 'Prompt is required' });

    const config: any = {
      tools: [{ googleMaps: {} }],
    };

    if (latitude !== undefined && longitude !== undefined) {
      config.toolConfig = {
        retrievalConfig: {
          latLng: {
            latitude: Number(latitude),
            longitude: Number(longitude),
          },
        },
      };
    }

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config,
    });

    const mapPlaces: Array<{ uri: string; title: string; reviewSnippets?: string[] }> = [];
    const chunks = response.candidates?.[0]?.groundingMetadata?.groundingChunks;
    if (chunks) {
      for (const chunk of chunks as any[]) {
        if (chunk.maps?.uri) {
          mapPlaces.push({
            uri: chunk.maps.uri,
            title: chunk.maps.title || 'View on Google Maps',
            reviewSnippets: chunk.maps.placeAnswerSources?.reviewSnippets || [],
          });
        }
      }
    }

    return res.json({
      text: response.text ?? '',
      places: mapPlaces,
    });
  } catch (error: any) {
    console.error('Maps grounding error:', error);
    return res.status(500).json({ error: error.message || 'Maps grounding failed' });
  }
});

// 4. Audio Transcription with gemini-3.5-transcribe
app.post('/api/gemini/transcribe', async (req: Request, res: Response) => {
  try {
    const { audioData, mimeType = 'audio/webm' } = req.body;
    if (!audioData) return res.status(400).json({ error: 'Audio data is required' });

    // Clean data if base64 URI prefix is present
    const base64Data = audioData.includes('base64,') ? audioData.split('base64,')[1] : audioData;

    const audioPart = {
      inlineData: {
        mimeType,
        data: base64Data,
      },
    };

    const response = await ai.models.generateContent({
      model: 'gemini-3.5-transcribe',
      contents: { parts: [audioPart, { text: 'Transcribe this audio clearly in the spoken language (Bengali or English).' }] },
    });

    return res.json({
      text: response.text ?? '',
    });
  } catch (error: any) {
    console.error('Transcription error:', error);
    return res.status(500).json({ error: error.message || 'Transcription failed' });
  }
});

// 5. Image Generation with gemini-nano-banana-2.1 (supports aspect ratio, resolution)
app.post('/api/gemini/generate-image', async (req: Request, res: Response) => {
  try {
    const { prompt, aspectRatio = '1:1', imageSize = '1K' } = req.body;
    if (!prompt) return res.status(400).json({ error: 'Prompt is required' });

    try {
      const response = await ai.models.generateContent({
        model: 'gemini-nano-banana-2.1',
        contents: {
          parts: [{ text: prompt }],
        },
        config: {
          imageConfig: {
            aspectRatio,
            imageSize,
          },
        },
      });

      for (const part of response.candidates?.[0]?.content?.parts ?? []) {
        if (part.inlineData?.data) {
          const mime = part.inlineData.mimeType ?? 'image/png';
          return res.json({
            imageUrl: `data:${mime};base64,${part.inlineData.data}`,
            model: 'gemini-nano-banana-2.1',
          });
        }
      }
      return res.json({ text: response.text ?? 'Image generation finished without binary data.' });
    } catch (nanoErr: any) {
      // Fallback to gemini-3.1-flash-lite-image if paid key not present
      console.warn('gemini-nano-banana-2.1 failed, falling back to gemini-3.1-flash-lite-image:', nanoErr.message);
      const fallbackResponse = await ai.models.generateContent({
        model: 'gemini-3.1-flash-lite-image',
        contents: { parts: [{ text: prompt }] },
      });
      for (const part of fallbackResponse.candidates?.[0]?.content?.parts ?? []) {
        if (part.inlineData?.data) {
          const mime = part.inlineData.mimeType ?? 'image/png';
          return res.json({
            imageUrl: `data:${mime};base64,${part.inlineData.data}`,
            model: 'gemini-3.1-flash-lite-image',
            note: 'Generated with gemini-3.1-flash-lite-image',
          });
        }
      }
      throw nanoErr;
    }
  } catch (error: any) {
    console.error('Image generation error:', error);
    return res.status(500).json({ error: error.message || 'Image generation failed' });
  }
});

// 6. Image Editing with gemini-nano-banana-2.1
app.post('/api/gemini/edit-image', async (req: Request, res: Response) => {
  try {
    const { prompt, sourceImage, mimeType = 'image/png', aspectRatio = '1:1' } = req.body;
    if (!prompt || !sourceImage) return res.status(400).json({ error: 'Prompt and source image are required' });

    const base64Data = sourceImage.includes('base64,') ? sourceImage.split('base64,')[1] : sourceImage;

    try {
      const response = await ai.models.generateContent({
        model: 'gemini-nano-banana-2.1',
        contents: {
          parts: [
            { inlineData: { mimeType, data: base64Data } },
            { text: prompt },
          ],
        },
        config: {
          imageConfig: { aspectRatio },
        },
      });

      for (const part of response.candidates?.[0]?.content?.parts ?? []) {
        if (part.inlineData?.data) {
          const mime = part.inlineData.mimeType ?? 'image/png';
          return res.json({
            imageUrl: `data:${mime};base64,${part.inlineData.data}`,
            model: 'gemini-nano-banana-2.1',
          });
        }
      }
      return res.json({ text: response.text ?? 'Edit completed.' });
    } catch (editErr: any) {
      console.warn('nano banana edit failed, trying flash lite:', editErr.message);
      const fallbackResponse = await ai.models.generateContent({
        model: 'gemini-3.1-flash-lite-image',
        contents: {
          parts: [
            { inlineData: { mimeType, data: base64Data } },
            { text: prompt },
          ],
        },
      });
      for (const part of fallbackResponse.candidates?.[0]?.content?.parts ?? []) {
        if (part.inlineData?.data) {
          const mime = part.inlineData.mimeType ?? 'image/png';
          return res.json({
            imageUrl: `data:${mime};base64,${part.inlineData.data}`,
            model: 'gemini-3.1-flash-lite-image',
          });
        }
      }
      throw editErr;
    }
  } catch (error: any) {
    console.error('Image edit error:', error);
    return res.status(500).json({ error: error.message || 'Image edit failed' });
  }
});

// 7. Video Generation from text with gemini-omni-1.1-flash via Interactions API
app.post('/api/gemini/generate-video', async (req: Request, res: Response) => {
  try {
    const { prompt, aspectRatio = '16:9' } = req.body;
    if (!prompt) return res.status(400).json({ error: 'Prompt is required' });

    const interaction = await ai.interactions.create({
      model: 'gemini-omni-1.1-flash',
      input: prompt,
      background: false,
      store: false,
      stream: false,
      response_format: {
        type: 'video',
        aspect_ratio: aspectRatio === '9:16' ? '9:16' : '16:9',
        duration: '5s',
        resolution: '720p',
      },
    }, { timeout: 300000 });

    const videoPart = interaction.output_video;
    if (videoPart && videoPart.data) {
      const mime = videoPart.mime_type || 'video/mp4';
      return res.json({
        videoUrl: `data:${mime};base64,${videoPart.data}`,
        duration: '5s',
      });
    }

    return res.json({
      status: interaction.status,
      message: 'Video processing status received',
    });
  } catch (error: any) {
    console.error('Video generation error:', error);
    return res.status(500).json({ error: error.message || 'Video generation requires a paid API key for gemini-omni-1.1-flash.' });
  }
});

// 8. Animate Image into Video with gemini-omni-1.1-flash via Interactions API
app.post('/api/gemini/animate-image', async (req: Request, res: Response) => {
  try {
    const { prompt, sourceImage, mimeType = 'image/png', aspectRatio = '16:9' } = req.body;
    if (!sourceImage) return res.status(400).json({ error: 'Source image is required' });

    const base64Data = sourceImage.includes('base64,') ? sourceImage.split('base64,')[1] : sourceImage;

    const interaction = await ai.interactions.create({
      model: 'gemini-omni-1.1-flash',
      input: [
        {
          type: 'image',
          mime_type: mimeType,
          data: base64Data,
        },
        {
          type: 'text',
          text: prompt || 'Animate this product naturally with subtle ambient light and camera pan.',
        },
      ],
      background: false,
      store: false,
      stream: false,
      response_format: {
        type: 'video',
        aspect_ratio: aspectRatio === '9:16' ? '9:16' : '16:9',
      },
    }, { timeout: 300000 });

    const videoPart = interaction.output_video;
    if (videoPart && videoPart.data) {
      const mime = videoPart.mime_type || 'video/mp4';
      return res.json({
        videoUrl: `data:${mime};base64,${videoPart.data}`,
      });
    }

    return res.json({
      status: interaction.status,
      message: 'Animation processing finished',
    });
  } catch (error: any) {
    console.error('Animate image error:', error);
    return res.status(500).json({ error: error.message || 'Image animation requires a paid API key for gemini-omni-1.1-flash.' });
  }
});

// 9. Music Generation with lyria-3-clip-preview / lyria-3-pro-preview
app.post('/api/gemini/generate-music', async (req: Request, res: Response) => {
  try {
    const { prompt, model = 'lyria-3-clip-preview' } = req.body;
    if (!prompt) return res.status(400).json({ error: 'Music prompt is required' });

    const selectedModel = model === 'lyria-3-pro-preview' ? 'lyria-3-pro-preview' : 'lyria-3-clip-preview';

    const responseStream = await ai.models.generateContentStream({
      model: selectedModel,
      contents: prompt,
    });

    const audioChunks: Buffer[] = [];
    let lyrics = '';
    let mimeType = 'audio/mpeg';

    for await (const chunk of responseStream) {
      const parts = chunk.candidates?.[0]?.content?.parts;
      if (!parts) continue;
      for (const part of parts) {
        if (part.inlineData?.data) {
          if (audioChunks.length === 0 && part.inlineData.mimeType) {
            mimeType = part.inlineData.mimeType;
          }
          audioChunks.push(Buffer.from(part.inlineData.data, 'base64'));
        }
        if (part.text) {
          lyrics += part.text;
        }
      }
    }

    if (audioChunks.length === 0) {
      return res.status(500).json({ error: 'No audio data received from music model' });
    }

    const audioBase64 = Buffer.concat(audioChunks).toString('base64');
    const audioDataUrl = `data:${mimeType};base64,${audioBase64}`;

    return res.json({
      audioUrl: audioDataUrl,
      lyrics,
      model: selectedModel,
    });
  } catch (error: any) {
    console.error('Music generation error:', error);
    return res.status(500).json({ error: error.message || 'Music generation requires a paid API key for Lyria.' });
  }
});

// 10. Bioscience & Agro-Food Quality Skills (PubChem & Gemini Scientific Analysis)
app.get('/api/science/pubchem/:compound', async (req: Request, res: Response) => {
  try {
    const compound = req.params.compound;
    const cidRes = await fetch(`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(compound)}/cids/JSON`);
    if (!cidRes.ok) {
      return res.status(404).json({ error: `Compound ${compound} not found in PubChem` });
    }
    const cidData = await cidRes.json();
    const cid = cidData?.IdentifierList?.CID?.[0];

    const propRes = await fetch(
      `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,InChIKey,XLogP,TPSA,Complexity/JSON`
    );
    const propData = await propRes.json();
    const props = propData?.PropertyTable?.Properties?.[0] || {};

    return res.json({
      name: compound,
      cid,
      ...props,
    });
  } catch (error: any) {
    return res.status(500).json({ error: error.message });
  }
});

app.post('/api/science/analyze-product', async (req: Request, res: Response) => {
  try {
    const { productName, category, details } = req.body;
    const prompt = `Perform a rigorous food science and agricultural biochemistry analysis for "${productName}" (Category: ${category}). Details: ${details || 'Standard local market produce'}.
Provide:
1. Biochemical nutrition profile (proteins, essential fatty acids, vitamins, minerals).
2. Food safety protocols (e.g. testing for formaldehyde/formalin, calcium carbide, microbial spoilage).
3. Post-harvest preservation & cold-chain parameters (temperature, humidity, active shelf life).
4. Relevant PubChem chemical compounds for preservation indicators.`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        systemInstruction: 'You are an expert food scientist and bio-agricultural quality control inspector for Bangladesh agricultural produce.',
      },
    });

    return res.json({
      analysis: response.text ?? '',
    });
  } catch (error: any) {
    return res.status(500).json({ error: error.message });
  }
});

// 11. WebSocket Server for Real-Time Gemini Live API (gemini-3.8-live)
const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  const { pathname } = new URL(request.url || '', `http://${request.headers.host}`);
  if (pathname === '/live') {
    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit('connection', ws, request);
    });
  }
});

wss.on('connection', async (clientWs: WebSocket) => {
  console.log('Client connected to Live Voice API');
  try {
    const session = await ai.live.connect({
      model: 'gemini-3.8-live',
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: {
          voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Zephyr' } },
        },
        systemInstruction: 'You are the real-time voice assistant for NexHaat marketplace in Bangladesh. Speak in natural conversational tones, helping users find products, track orders, or learn about fresh seasonal foods.',
      },
      callbacks: {
        onmessage: (message: any) => {
          for (const part of message.serverContent?.modelTurn?.parts ?? []) {
            if (part.inlineData?.data) {
              clientWs.send(JSON.stringify({ audio: part.inlineData.data }));
            }
          }
          if (message.serverContent?.interrupted) {
            clientWs.send(JSON.stringify({ interrupted: true }));
          }
        },
      },
    });

    clientWs.on('message', (data: Buffer) => {
      try {
        const parsed = JSON.parse(data.toString());
        if (parsed.audio) {
          session.sendRealtimeInput({
            audio: { data: parsed.audio, mimeType: 'audio/pcm;rate=16000' },
          });
        }
      } catch (err) {
        console.error('Error forwarding audio to Live session:', err);
      }
    });

    clientWs.on('close', () => {
      console.log('Client disconnected from Live Voice API');
    });
  } catch (liveError: any) {
    console.error('Failed to initialize Live API session:', liveError);
    clientWs.send(JSON.stringify({ error: liveError.message || 'Live API connection error' }));
  }
});

// Mount Vite middleware in development or serve static in production
const isProduction = process.env.NODE_ENV === 'production';
if (!isProduction) {
  const { createServer: createViteServer } = await import('vite');
  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: 'spa',
  });
  app.use(vite.middlewares);
} else {
  const distPath = path.resolve(__dirname, 'dist');
  app.use(express.static(distPath));
  app.get('*', (_req, res) => {
    res.sendFile(path.resolve(distPath, 'index.html'));
  });
}

const PORT = 3000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`NexHaat server running on http://0.0.0.0:${PORT}`);
});
