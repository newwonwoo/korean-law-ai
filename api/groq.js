export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  if (req.method === 'OPTIONS') return res.status(200).end()
  if (req.method !== 'POST') return res.status(405).end()

  const GROQ_KEY = process.env.GROQ_API_KEY
  if (!GROQ_KEY) return res.status(500).json({ error: 'GROQ_API_KEY 환경변수 미설정' })

  const { messages, max_tokens = 1500 } = req.body

  const upstream = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${GROQ_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'llama-3.3-70b-versatile',
      messages,
      max_tokens,
      temperature: 0.3
    })
  })

  const data = await upstream.json()
  res.status(upstream.status).json(data)
}
