// Vercel Serverless Function - API 代理
export default async function handler(req, res) {
  const { path } = req.query;

  // 构建后端 URL
  const pathStr = Array.isArray(path) ? path.join('/') : (path || '');
  const backendUrl = `http://119.45.167.80:8000/api/${pathStr}`;

  // 添加查询参数
  const url = new URL(backendUrl);
  Object.keys(req.query).forEach(key => {
    if (key !== 'path') {
      url.searchParams.set(key, req.query[key]);
    }
  });

  try {
    const response = await fetch(url.toString(), {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
