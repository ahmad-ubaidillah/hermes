# gateway/run.py Structure Analysis

**File**: gateway/run.py
**Lines**: 6,900
**Classes**: 1 main (`GatewayRunner` class)
**Functions**: ~20 utility functions

## GatewayRunner Class Structure

### Key Components (lines 478-6600)

```python
class GatewayRunner:
    def __init__(self, ...):              # Initialization
    def start_gateway(self):             # Main entry point
    def _start_cron_ticker(self, ...):    # Cron scheduling
```

## Utility Functions (lines 36-470)

### 1. SSL/Certificate Management
```python
def _ensure_ssl_certs() -> None:        # Line 36
    # Ensures SSL certificates are properly configured
```

### 2. WhatsApp Integration
```python
def _normalize_whatsapp_identifier(value: str) -> str:    # Line 235
    # Normalizes WhatsApp phone number format

def _expand_whatsapp_auth_aliases(identifier: str) -> set:    # Line 241
    # Expands WhatsApp auth aliases for multiple formats
```

### 3. Message Handling
```python
def _get_max_message_length(config: Optional[dict] = None) -> int:    # Line 285
    # Gets max message length from config

def _sanitize_message(text: str, config: Optional[dict] = None) -> str:    # Line 299
    # Sanitizes message content

def _validate_message_length(text: str, max_length: int) -> Optional[str]:    # Line 311
    # Validates message length

def _validate_message(...) -> Optional[str]:    # Line 323
    # Validates complete message
```

### 4. Agent Configuration
```python
def _resolve_runtime_agent_kwargs() -> dict:    # Line 350
    # Resolves runtime agent kwargs

def _check_unavailable_skill(command_name: str) -> str | None:    # Line 373
    # Checks if skill is unavailable

def _platform_config_key(platform: "Platform") -> str:    # Line 418
    # Gets platform config key

def _load_gateway_config() -> dict:    # Line 422
    # Loads gateway configuration

def _resolve_gateway_model(config: dict | None = None) -> str:    # Line 437
    # Resolves gateway model

def _resolve_aizen_bin() -> Optional[list[str]]:    # Line 452
    # Resolves aizen binary path
```

## Modularization Opportunities

### 1. Extract Message Validation (Lines 285-350)
**New file**: `gateway/validation.py`
```python
- _get_max_message_length()
- _sanitize_message()
- _validate_message_length()
- _validate_message()
```
**Estimated lines**: 200-300

### 2. Extract WhatsApp Utilities (Lines 235-280)
**New file**: `gateway/whatsapp_utils.py`
```python
- _normalize_whatsapp_identifier()
- _expand_whatsapp_auth_aliases()
```
**Estimated lines**: 100-150

### 3. Extract Configuration Management (Lines 350-470)
**New file**: `gateway/config.py`
```python
- _resolve_runtime_agent_kwargs()
- _check_unavailable_skill()
- _platform_config_key()
- _load_gateway_config()
- _resolve_gateway_model()
- _resolve_aizen_bin()
```
**Estimated lines**: 300-400

### 4. Extract SSL Management (Lines 36-234)
**New file**: `gateway/ssl_utils.py`
```python
- _ensure_ssl_certs()
    # Plus related SSL certificate logic
```
**Estimated lines**: 200-300

## Recommended Extraction Order

1. **gateway/validation.py** (Low risk) - Message validation only
2. **gateway/whatsapp_utils.py** (Low risk) - WhatsApp-specific utilities
3. **gateway/ssl_utils.py** (Medium risk) - SSL certificate management
4. **gateway/config.py** (High risk) - Configuration management

## Estimated Effort: 6-10 hours

---
*Analysis completed by: Sisyphus Agent*
*Ready for: Implementation (if needed)*