// Backend targets for index.html.
// mock:  in-browser stub, no network. Default when index.html is opened as a file.
// local: python3.13 local_server.py, then open http://localhost:8787/
// cloud: API Gateway + Cognito. Values come from config.cloud.js, which Terraform writes.
window.INDO_CONFIG = {
  // Served by local_server.py (or the desktop app): start on LOCAL.
  defaultTarget: location.protocol.startsWith('http') ? 'local' : 'mock',
  local: {
    // The page and the backend share an origin; opened as a file, fall back to the default port.
    baseUrl: location.protocol.startsWith('http') ? location.origin : 'http://127.0.0.1:8787',
  },
  cloud: Object.assign({
    baseUrl: '',
    cognito: { domain: '', clientId: '', redirectUri: 'http://localhost:8787/' },
  }, window.INDO_CLOUD || {}),
};
