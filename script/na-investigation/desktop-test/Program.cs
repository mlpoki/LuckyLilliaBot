using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using LuckyLilliaDesktop.Services;
using Microsoft.Extensions.Logging.Abstractions;

var listener = new TcpListener(IPAddress.Loopback, 0);
listener.Start();
var port = ((IPEndPoint)listener.LocalEndpoint).Port;
Environment.SetEnvironmentVariable("LILLIA_AUTH_BASE_URL", $"http://127.0.0.1:{port}");
var requests = new List<object>();
var server = Task.Run(async () => {
    foreach (var code in new[] { 200, 401, 403, 503 }) {
        using var socket = await listener.AcceptTcpClientAsync();
        using var stream = socket.GetStream();
        using var reader = new StreamReader(stream, Encoding.ASCII, leaveOpen: true);
        var request = await reader.ReadLineAsync();
        var headers = new List<string>();
        string? line;
        while (!string.IsNullOrEmpty(line = await reader.ReadLineAsync())) headers.Add(line);
        if (request != "GET /api/sign/info HTTP/1.1" || !headers.Contains("Authorization: Bearer fixture"))
            throw new Exception("Unexpected preflight request");
        requests.Add(new { address = socket.Client.LocalEndPoint!.ToString(), request, code });
        await stream.WriteAsync(Encoding.ASCII.GetBytes($"HTTP/1.1 {code} Fixture\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"));
    }
});
var validator = new AuthTokenValidator(NullLogger<AuthTokenValidator>.Instance);
var results = new List<object>();
async Task Check(string name, string token, AuthTokenValidationStatus expected) {
    var actual = await validator.ValidateAsync(token);
    if (actual.Status != expected) throw new Exception($"{name}: expected {expected}, got {actual.Status}");
    results.Add(new { name, passed = true, status = actual.Status.ToString() });
}
await Check("empty rejected without request", "  ", AuthTokenValidationStatus.Invalid);
if (requests.Count != 0) throw new Exception("Empty token performed network request");
await Check("2xx accepted; token trimmed", " fixture ", AuthTokenValidationStatus.Valid);
await Check("401 rejected", "fixture", AuthTokenValidationStatus.Invalid);
await Check("403 rejected", "fixture", AuthTokenValidationStatus.Invalid);
await Check("503 inconclusive", "fixture", AuthTokenValidationStatus.Inconclusive);
await server;
listener.Stop();
await Check("unreachable loopback inconclusive", "fixture", AuthTokenValidationStatus.Inconclusive);
File.WriteAllText("evidence/desktop-tests.json", JsonSerializer.Serialize(new {
    sourceCommit = "a718675d6916fcf013e5929ddffe464fbd750c03", results, requests,
    scope = "Unmodified public Desktop preflight validator only. No GUI, PMHQ, native code, token issuance, real signature or QQ login executed."
}, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"{results.Count} Desktop preflight checks passed; {requests.Count} loopback requests");
