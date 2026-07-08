# RDLLM API Client Examples

These examples use only each language's standard HTTP client where practical.
Start the service first:

```bash
export RDLLM_SERVICE_TOKEN="${RDLLM_SERVICE_TOKEN:-rdllm-local-dev-token}"
export RDLLM_SERVICE_TOKEN_SHA256="$(python - <<'PY'
import hashlib
import os
print(hashlib.sha256(os.environ["RDLLM_SERVICE_TOKEN"].encode()).hexdigest())
PY
)"
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

All examples call:

```text
POST http://127.0.0.1:8765/v1/attribute
Authorization: Bearer rdllm-local-dev-token
```

## JavaScript

```javascript
const response = await fetch("http://127.0.0.1:8765/v1/attribute", {
  method: "POST",
  headers: {
    "Authorization": "Bearer rdllm-local-dev-token",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    prompt: "What should royalty-bearing AI answers expose?",
    output: "Every royalty-bearing AI answer should expose grounded sources, claim evidence, and payout or escrow state.",
    gross_revenue: "1.00"
  })
});

const result = await response.json();
console.log(result.status);
console.log(result.display.rendered_text);
console.log(result.source_footer.rendered_text);
```

## Python

```python
import json
from urllib.request import Request, urlopen

payload = {
    "prompt": "What should royalty-bearing AI answers expose?",
    "output": (
        "Every royalty-bearing AI answer should expose grounded sources, "
        "claim evidence, and payout or escrow state."
    ),
    "gross_revenue": "1.00",
}

request = Request(
    "http://127.0.0.1:8765/v1/attribute",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": "Bearer rdllm-local-dev-token",
        "Content-Type": "application/json",
    },
    method="POST",
)

with urlopen(request) as response:
    result = json.loads(response.read().decode("utf-8"))

print(result["status"])
print(result["display"]["rendered_text"])
print(result["source_footer"]["rendered_text"])
```

## TypeScript

```typescript
type AttributionResponse = {
  status: "ready" | "blocked";
  display: { rendered_text: string };
  source_footer: { rendered_text: string };
};

const response = await fetch("http://127.0.0.1:8765/v1/attribute", {
  method: "POST",
  headers: {
    "Authorization": "Bearer rdllm-local-dev-token",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    prompt: "What should royalty-bearing AI answers expose?",
    output: "Every royalty-bearing AI answer should expose grounded sources, claim evidence, and payout or escrow state.",
    gross_revenue: "1.00"
  })
});

const result = (await response.json()) as AttributionResponse;
console.log(result.status);
console.log(result.display.rendered_text);
console.log(result.source_footer.rendered_text);
```

## Java

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class RdllmExample {
  public static void main(String[] args) throws Exception {
    String body = """
      {
        "prompt": "What should royalty-bearing AI answers expose?",
        "output": "Every royalty-bearing AI answer should expose grounded sources, claim evidence, and payout or escrow state.",
        "gross_revenue": "1.00"
      }
      """;

    HttpRequest request = HttpRequest.newBuilder()
      .uri(URI.create("http://127.0.0.1:8765/v1/attribute"))
      .header("Authorization", "Bearer rdllm-local-dev-token")
      .header("Content-Type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(body))
      .build();

    HttpResponse<String> response = HttpClient.newHttpClient()
      .send(request, HttpResponse.BodyHandlers.ofString());

    System.out.println(response.body());
  }
}
```

## C#

```csharp
using System.Net.Http;
using System.Text;

using var client = new HttpClient();
using var request = new HttpRequestMessage(
    HttpMethod.Post,
    "http://127.0.0.1:8765/v1/attribute"
);

request.Headers.Add("Authorization", "Bearer rdllm-local-dev-token");
request.Content = new StringContent(
    """
    {
      "prompt": "What should royalty-bearing AI answers expose?",
      "output": "Every royalty-bearing AI answer should expose grounded sources, claim evidence, and payout or escrow state.",
      "gross_revenue": "1.00"
    }
    """,
    Encoding.UTF8,
    "application/json"
);

using var response = await client.SendAsync(request);
Console.WriteLine(await response.Content.ReadAsStringAsync());
```

## What To Check In Any Language

After parsing the response, do not display the answer as grounded unless:

- `status` is `ready`;
- `display.rendered_text` contains the answer and footer;
- `source_footer.rendered_text` contains `Sources` and `Claim Evidence`;
- verifier output reports `production_display_ready: true`;
- `claim_source_disagreement_status` is `passed`;
- the copied/exported answer still contains verifier handles and source rows.

For complete runtime commands, see [live use cases](../live_use_cases/README.md).
