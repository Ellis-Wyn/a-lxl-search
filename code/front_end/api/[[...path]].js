/**
 * Vercel Serverless Function - API 代理 (Catch-all)
 *
 * 将前端 HTTPS 请求转发到后端 HTTP 服务器
 * 解决混合内容（Mixed Content）问题
 *
 * 使用方式: /api/xxx → http://119.45.167.80:8000/api/xxx
 */

export default async function handler(req, res) {
  // 只允许 GET 和 POST 请求
  if (!['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'].includes(req.method)) {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // 处理 OPTIONS 预检请求
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    return res.status(200).end();
  }

  try {
    // 获取要代理的路径
    const { path } = req.query;
    const pathStr = Array.isArray(path) ? path.join('/') : path || '';

    // 构建后端 URL
    const backendUrl = `http://119.45.167.80:8000/api/${pathStr}`;

    // 构建查询参数
    const url = new URL(backendUrl);
    Object.keys(req.query).forEach(key => {
      if (key !== 'path') {
        url.searchParams.set(key, req.query[key]);
      }
    });

    // 转发请求到后端
    const response = await fetch(url.toString(), {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
    });

    // 获取响应数据
    const data = await response.json();

    // 返回响应
    res.status(response.status).json(data);
  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({ error: 'Proxy error', message: error.message });
  }
}
