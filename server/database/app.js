const http = require('http');
const fs = require('fs');
const path = require('path');

const port = process.env.PORT || 3030;

const reviewsData = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'reviews.json'), 'utf8'));
const dealershipsData = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'dealerships.json'), 'utf8'));

let reviewsStore = Array.isArray(reviewsData.reviews) ? [...reviewsData.reviews] : [];
let dealershipsStore = Array.isArray(dealershipsData.dealerships) ? [...dealershipsData.dealerships] : [];

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(payload));
}

function sendText(res, statusCode, payload) {
  res.writeHead(statusCode, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end(payload);
}

function readRequestBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];

    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

function getNextId(items) {
  return items.length ? Math.max(...items.map((item) => Number(item.id) || 0)) + 1 : 1;
}

const server = http.createServer(async (req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host}`);
  const { pathname } = requestUrl;

  if (req.method === 'GET' && pathname === '/') {
    sendText(res, 200, 'Welcome to the local Mongoose API');
    return;
  }

  if (req.method === 'GET' && pathname === '/fetchReviews') {
    sendJson(res, 200, reviewsStore);
    return;
  }

  if (req.method === 'GET' && pathname.startsWith('/fetchReviews/dealer/')) {
    const dealerId = Number(pathname.split('/').pop());
    const documents = reviewsStore.filter((review) => Number(review.dealership) === dealerId);
    sendJson(res, 200, documents);
    return;
  }

  if (req.method === 'GET' && pathname === '/fetchDealers') {
    sendJson(res, 200, dealershipsStore);
    return;
  }

  if (req.method === 'GET' && pathname.startsWith('/fetchDealers/')) {
    const state = decodeURIComponent(pathname.split('/').pop());
    const documents = dealershipsStore.filter((dealership) => dealership.state === state);
    sendJson(res, 200, documents);
    return;
  }

  if (req.method === 'GET' && pathname.startsWith('/fetchDealer/')) {
    const dealerId = Number(pathname.split('/').pop());
    const document = dealershipsStore.find((dealership) => Number(dealership.id) === dealerId) || null;
    sendJson(res, 200, document);
    return;
  }

  if (req.method === 'POST' && pathname === '/insert_review') {
    try {
      const rawBody = await readRequestBody(req);
      const data = JSON.parse(rawBody);
      const newReview = {
        id: getNextId(reviewsStore),
        name: data.name,
        dealership: data.dealership,
        review: data.review,
        purchase: data.purchase,
        purchase_date: data.purchase_date,
        car_make: data.car_make,
        car_model: data.car_model,
        car_year: data.car_year,
      };

      reviewsStore = [...reviewsStore, newReview];
      sendJson(res, 200, newReview);
    } catch (error) {
      sendJson(res, 500, { error: 'Error inserting review' });
    }
    return;
  }

  sendJson(res, 404, { error: 'Not found' });
});

server.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});