const http = require('node:http');

const port = Number(process.env.PORT ?? 3000);

const server = http.createServer((_, response) => {
  response.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
  response.end('ATrade frontend bootstrap\n');
});

server.listen(port, () => {
  process.stdout.write(`frontend listening on ${port}\n`);
});
