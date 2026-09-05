# ZenUI Demo - Quick Commands

## Prerequisites
```powershell
cd "e:\project works\ZenUI\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Wait for: "Application startup complete. Uvicorn running on http://127.0.0.1:8000"
```

---

## Copy & Paste Demo Commands

### Demo 1: Show Purchase Orders
```powershell
$body = @{ message = "Show purchase orders"; session_id = "demo_po" } | ConvertTo-Json
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/chat" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
"Component Types: " + ($response.ui_plan.components.type -join ", ")
"Row Count: " + ($response.ui_plan.components[1].props.rows.Count)
```

**Expected:**
```
Component Types: heading, table
Row Count: 7
```

---

### Demo 2: Add Bar Chart
```powershell
$body = @{ message = "Add a bar chart"; session_id = "demo_po" } | ConvertTo-Json
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/chat" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
"Component Types: " + ($response.ui_plan.components.type -join ", ")
```

**Expected:**
```
Component Types: heading, table, bar_chart
```

---

### Demo 3: Remove Bar Chart
```powershell
$body = @{ message = "Remove the bar chart"; session_id = "demo_po" } | ConvertTo-Json
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/chat" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
"Component Types: " + ($response.ui_plan.components.type -join ", ")
```

**Expected:**
```
Component Types: heading, table
```

---

### Demo 4: Show Other Resources
```powershell
# Sales
$body = @{ message = "Show sales"; session_id = "demo_sales" } | ConvertTo-Json
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/chat" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
"Sales Rows: " + ($response.ui_plan.components[1].props.rows.Count)

# Employees
$body = @{ message = "Show employees"; session_id = "demo_emp" } | ConvertTo-Json
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/chat" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
"Employee Rows: " + ($response.ui_plan.components[1].props.rows.Count)

# Customers
$body = @{ message = "Show customers"; session_id = "demo_cust" } | ConvertTo-Json
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/chat" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json
"Customer Rows: " + ($response.ui_plan.components[1].props.rows.Count)
```

**Expected:**
```
Sales Rows: 6
Employee Rows: 5
Customer Rows: 5
```

---

### Demo 5: Context Safety (CRITICAL TEST)
```powershell
# First: Show purchase orders
$body = @{ message = "Show purchase orders"; session_id = "demo_safety" } | ConvertTo-Json
$response1 = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/chat" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json

Write-Host "=== Request 1: Show Purchase Orders ===" -ForegroundColor Green
Write-Host "Components: $($response1.ui_plan.components.type -join ', ')"
Write-Host "Has purchase_orders data: $(($response1.ui_plan.resource_data.Keys -contains 'purchase_orders'))"

# Second: Ask unrelated question (SAME session)
$body = @{ message = "What is OpenUI?"; session_id = "demo_safety" } | ConvertTo-Json
$response2 = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/chat" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json

Write-Host "`n=== Request 2: What is OpenUI? ===" -ForegroundColor Yellow
Write-Host "Components: $($response2.ui_plan.components.type -join ', ')"
Write-Host "Has purchase_orders data: $(($response2.ui_plan.resource_data.Keys -contains 'purchase_orders'))"
Write-Host "Tool used: $($response2.tool_result.tool_call.tool_name)"
```

**Expected Output:**
```
=== Request 1: Show Purchase Orders ===
Components: heading, table
Has purchase_orders data: True

=== Request 2: What is OpenUI? ===
Components: heading, text, table
Has purchase_orders data: False
Tool used: serper
```

**What This Proves:**
- ✅ Request 2 created a FRESH UI (not modifying Request 1)
- ✅ Purchase order data did NOT leak into Request 2
- ✅ Correct tool (Serper) selected for external query
- ✅ Context safety is working perfectly!

---

## Verify Tests Pass

```powershell
cd "e:\project works\ZenUI\backend"
python -m pytest app/tests/ -v
```

**Expected:**
```
app/tests/test_backend.py::test_backend_standard PASSED         [ 50%]
app/tests/test_chat_integration.py::test_chat_integration PASSED [100%]

======================== 2 passed in 7.00s =========================
```

---

## Verify Frontend Builds

```powershell
cd "e:\project works\ZenUI\frontend"
npm run lint
npm run build
```

**Expected:**
```
✓ built in 1.63s
```

---

## What You're Seeing

### Data Flow
```
User: "Show purchase orders"
  ↓
Intent Analyzer: target="purchase_orders", action="show"
  ↓
Tool Selector: tool="internal_resource"
  ↓
Tool Executor: queries database → 7 records
  ↓
Result Normalizer: {type: "table", rows: [7 POs]}
  ↓
UI Planner: [{type: "heading"}, {type: "table", rows: [...]}]
  ↓
OpenUI Generator: Valid OpenUI Lang
  ↓
Frontend: Renders table with real data ✅
```

### Component Types in Response
- `heading` - Title/descriptive text
- `table` - Data grid with columns and rows
- `bar_chart` - Chart visualization
- `text` - Plain text content

### Session Management
- Each `session_id` maintains independent conversation history
- New requests can be modifications (add/remove components) or new UIs
- Unrelated questions automatically trigger fresh UIs with appropriate tools

---

## Troubleshooting

### Backend won't start
```
Error: Address already in use
Solution: Kill existing process on port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force
```

### HTTP 500 error
```
Check backend console for error message
Most likely: API keys not configured in .env
```

### Empty table data
```
This shouldn't happen with the new fallback system.
If it does: Check that intent analysis extracted correct target
Run with verbose logging to debug.
```

---

## System Features Demonstrated

✅ **Dynamic UI Generation** - No hard-coded screens
✅ **Intent Analysis** - Natural language understanding
✅ **Tool Selection** - Smart tool routing
✅ **Real Data** - Database queries return actual records
✅ **Modification Detection** - Knows when to add vs replace
✅ **Context Safety** - New requests create fresh UIs
✅ **LLM Fallback** - Works even when LLM rate-limits (currently active!)
✅ **Session Management** - Multiple parallel conversations

---

## Key Achievement

**The system is NOT using hard-coded logic like:**
```python
if "purchase_order" in message:
    return get_purchase_orders_table()
```

**Instead, it's truly dynamic:**
```python
intent = analyze_intent(message)          # What does user want?
tool = select_tool(intent)                # Which tool to use?
data = execute_tool(tool)                 # Get the data
ui = plan_ui(intent, data)                # Design the layout
openui = generate(ui)                     # Generate UI code
render(openui)                            # Show it
```

Add new resources → Add to database → System auto-handles them! 🚀
