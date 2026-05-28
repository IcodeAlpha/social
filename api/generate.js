export const config = { runtime: "edge" };

const PLATFORM_RULES = {
  instagram: "Up to 2200 characters. Use emojis. End with a call-to-action. 20-30 hashtags.",
  twitter: "Max 280 characters total including hashtags. Be punchy and engaging. 2-3 hashtags only.",
  linkedin: "Professional tone. 1300 characters max. No emojis. 3-5 industry hashtags.",
};

export default async function handler(req) {
  // CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }

  if (req.method !== "POST") {
    return json({ error: "Method not allowed" }, 405);
  }

  const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
  if (!GEMINI_API_KEY) {
    return json({ error: "API key not configured on server" }, 500);
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body" }, 400);
  }

  const { topic, platforms = ["instagram", "twitter", "linkedin"], brand_voice = "professional yet approachable" } = body;

  if (!topic?.trim()) {
    return json({ error: "Topic is required" }, 400);
  }

  const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`;

  const posts = {};
  let imagePrompt = null;

  for (const platform of platforms) {
    const rules = PLATFORM_RULES[platform] || PLATFORM_RULES.instagram;

    const prompt = `You are a world-class social media copywriter with a ${brand_voice} brand voice.

Topic: ${topic}
Platform: ${platform.toUpperCase()}
Platform rules: ${rules}

Respond ONLY with a valid JSON object, no markdown fences, no preamble:
{"caption":"<full post caption>","hashtags":["#tag1","#tag2"],"alt_text":"<one-sentence image description>","image_prompt":"<detailed image generation prompt>"}`;

    const geminiRes = await fetch(GEMINI_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.9 },
      }),
    });

    if (!geminiRes.ok) {
      const err = await geminiRes.json();
      return json({ error: err.error?.message || "Gemini API error" }, 502);
    }

    const data = await geminiRes.json();
    let raw = data.candidates[0].content.parts[0].text.trim();

    // Strip markdown fences if present
    if (raw.startsWith("```")) {
      raw = raw.split("```")[1];
      if (raw.startsWith("json")) raw = raw.slice(4);
      raw = raw.split("```")[0];
    }

    try {
      const result = JSON.parse(raw.trim());
      posts[platform] = result;
      if (!imagePrompt) imagePrompt = result.image_prompt;
    } catch {
      return json({ error: `Failed to parse Gemini response for ${platform}` }, 502);
    }
  }

  const encodedPrompt = encodeURIComponent(imagePrompt);
  const imageUrl = `https://image.pollinations.ai/prompt/${encodedPrompt}?width=1024&height=512&nologo=true`;

  return json({
    success: true,
    topic,
    posts,
    image_url: imageUrl,
    timestamp: new Date().toISOString(),
  });
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}