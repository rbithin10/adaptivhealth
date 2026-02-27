# Nutrition Feature Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Run Database Migration

**SQLite (Development):**
```bash
cd c:\Users\hp\Desktop\AdpativHealth
sqlite3 adaptiv_health.db < migrations\add_nutrition_entries.sql
```

**Or using Python:**
```python
import sqlite3
conn = sqlite3.connect('adaptiv_health.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS nutrition_entries (
        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        meal_type VARCHAR(50) NOT NULL DEFAULT 'other',
        description TEXT,
        calories INTEGER NOT NULL,
        protein_grams INTEGER,
        carbs_grams INTEGER,
        fat_grams INTEGER,
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    )
''')

cursor.execute('CREATE INDEX IF NOT EXISTS idx_nutrition_user_timestamp ON nutrition_entries(user_id, timestamp)')
conn.commit()
conn.close()
print("✅ Migration complete!")
```

### 2. Start Backend Server

```bash
python start_server.py
```

Server runs on: `http://localhost:8080`  
API docs: `http://localhost:8080/docs`

### 3. Test the API

**Option A: Using Swagger UI** (Easiest)
1. Open `http://localhost:8080/docs`
2. Click "Authorize" → Enter credentials → Click "Authorize"
   - Username: `test@example.com`
   - Password: `password123`
3. Try endpoints:
   - POST `/api/v1/nutrition` → "Try it out" → Fill in meal_type and calories → Execute
   - GET `/api/v1/nutrition/recent` → "Try it out" → Execute
   - DELETE `/api/v1/nutrition/{entry_id}` → "Try it out" → Enter entry_id → Execute

**Option B: Using curl** (Command Line)
```bash
# 1. Login and get token
curl -X POST http://localhost:8080/api/v1/login \
  -F "username=test@example.com" \
  -F "password=password123"

# Copy the "access_token" value from response

# 2. Create nutrition entry
curl -X POST http://localhost:8080/api/v1/nutrition \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d "{\"meal_type\":\"breakfast\",\"calories\":350,\"description\":\"Oatmeal with berries\"}"

# 3. Get recent entries
curl -X GET "http://localhost:8080/api/v1/nutrition/recent?limit=5" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"

# 4. Delete entry (use entry_id from step 2 or 3)
curl -X DELETE "http://localhost:8080/api/v1/nutrition/123" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Option C: Using Python requests**
```python
import requests

BASE_URL = "http://localhost:8080/api/v1"

# 1. Login
response = requests.post(
    f"{BASE_URL}/login",
    data={"username": "test@example.com", "password": "password123"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Create entry
response = requests.post(
    f"{BASE_URL}/nutrition",
    json={
        "meal_type": "breakfast",
        "calories": 350,
        "description": "Oatmeal with berries",
        "protein_grams": 12
    },
    headers=headers
)
print("Created:", response.json())

# 3. Get recent entries
response = requests.get(
    f"{BASE_URL}/nutrition/recent?limit=5",
    headers=headers
)
print("Entries:", response.json())

# 4. Delete entry
entry_id = response.json()["entries"][0]["entry_id"]
response = requests.delete(
    f"{BASE_URL}/nutrition/{entry_id}",
    headers=headers
)
print("Deleted:", response.status_code == 204)
```

### 4. Run Tests

```bash
cd c:\Users\hp\Desktop\AdpativHealth
pytest tests\test_nutrition.py -v
```

**Expected output:**
```
tests/test_nutrition.py::TestNutritionEndpoints::test_create_nutrition_entry_success PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_create_nutrition_entry_minimal PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_create_nutrition_entry_unauthorized PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_create_nutrition_entry_invalid_meal_type PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_create_nutrition_entry_negative_calories PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_get_recent_nutrition_entries_empty PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_get_recent_nutrition_entries_with_data PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_get_recent_nutrition_entries_with_limit PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_get_recent_nutrition_entries_unauthorized PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_delete_nutrition_entry_success PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_delete_nutrition_entry_not_found PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_delete_nutrition_entry_unauthorized PASSED
tests/test_nutrition.py::TestNutritionEndpoints::test_user_can_only_access_own_entries PASSED

==================== 15 passed in 2.34s ====================
```

---

## 📱 Mobile App Integration

### Add Methods to ApiClient

**File:** `mobile-app/lib/services/api_client.dart`

```dart
// Add these methods to the ApiClient class

/// Create nutrition entry
Future<Map<String, dynamic>> createNutritionEntry({
  required String mealType,
  required int calories,
  String? description,
  int? proteinGrams,
  int? carbsGrams,
  int? fatGrams,
}) async {
  try {
    final response = await _dio.post(
      '/nutrition',
      data: {
        'meal_type': mealType,
        'calories': calories,
        if (description != null) 'description': description,
        if (proteinGrams != null) 'protein_grams': proteinGrams,
        if (carbsGrams != null) 'carbs_grams': carbsGrams,
        if (fatGrams != null) 'fat_grams': fatGrams,
      },
    );
    return response.data as Map<String, dynamic>;
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

/// Get recent nutrition entries
Future<Map<String, dynamic>> getRecentNutritionEntries({int limit = 5}) async {
  try {
    final response = await _dio.get(
      '/nutrition/recent',
      queryParameters: {'limit': limit},
    );
    return response.data as Map<String, dynamic>;
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

/// Delete nutrition entry
Future<void> deleteNutritionEntry(int entryId) async {
  try {
    await _dio.delete('/nutrition/$entryId');
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}
```

### Update NutritionScreen

**File:** `mobile-app/lib/screens/nutrition_screen.dart`

Replace hardcoded data with backend API calls:

```dart
class _NutritionScreenState extends State<NutritionScreen> {
  bool _isLoading = false;
  String? _errorMessage;
  List<Map<String, dynamic>> _entries = [];
  int _totalCount = 0;

  @override
  void initState() {
    super.initState();
    _loadNutritionEntries();
  }

  /// Load recent entries from backend
  Future<void> _loadNutritionEntries() async {
    setState(() => _isLoading = true);
    try {
      final data = await widget.apiClient.getRecentNutritionEntries(limit: 10);
      setState(() {
        _entries = List<Map<String, dynamic>>.from(data['entries']);
        _totalCount = data['total_count'];
        _errorMessage = null;
      });
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      setState(() => _isLoading = false);
    }
  }

  /// Create new entry
  Future<void> _createEntry({
    required String mealType,
    required int calories,
    String? description,
    int? proteinGrams,
    int? carbsGrams,
    int? fatGrams,
  }) async {
    try {
      await widget.apiClient.createNutritionEntry(
        mealType: mealType,
        calories: calories,
        description: description,
        proteinGrams: proteinGrams,
        carbsGrams: carbsGrams,
        fatGrams: fatGrams,
      );
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Meal logged successfully!')),
      );
      
      _loadNutritionEntries(); // Refresh list
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    }
  }

  /// Delete entry
  Future<void> _deleteEntry(int entryId) async {
    try {
      await widget.apiClient.deleteNutritionEntry(entryId);
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Entry deleted')),
      );
      
      _loadNutritionEntries(); // Refresh list
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Error: $_errorMessage'),
            ElevatedButton(
              onPressed: _loadNutritionEntries,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_entries.isEmpty) {
      return const Center(child: Text('No nutrition entries yet'));
    }

    return ListView.builder(
      itemCount: _entries.length,
      itemBuilder: (context, index) {
        final entry = _entries[index];
        return ListTile(
          title: Text('${entry['meal_type']} - ${entry['calories']} cal'),
          subtitle: Text(entry['description'] ?? 'No description'),
          trailing: IconButton(
            icon: const Icon(Icons.delete),
            onPressed: () => _deleteEntry(entry['entry_id']),
          ),
        );
      },
    );
  }
}
```

---

## 🔍 Verify Database

**Check table was created:**
```bash
sqlite3 adaptiv_health.db
.tables
# Should show: nutrition_entries

.schema nutrition_entries
# Should show the table structure
```

**Check sample data:**
```sql
sqlite3 adaptiv_health.db
SELECT * FROM nutrition_entries LIMIT 5;
```

---

## 📚 Documentation

- **API Reference:** `docs/NUTRITION_API.md` (426 lines)
- **Implementation Summary:** `docs/NUTRITION_IMPLEMENTATION_SUMMARY.md` (560 lines)
- **Database Migration:** `migrations/add_nutrition_entries.sql`
- **Tests:** `tests/test_nutrition.py` (323 lines, 15 test cases)

---

## ✅ Acceptance Checklist

- [ ] Database migration run successfully
- [ ] Backend server starts without errors
- [ ] Can create nutrition entry via API
- [ ] Can retrieve recent entries
- [ ] Can delete entry
- [ ] Tests pass (15/15)
- [ ] Swagger UI shows nutrition endpoints
- [ ] Mobile ApiClient updated
- [ ] NutritionScreen wired to backend
- [ ] End-to-end testing complete

---

## 🐛 Troubleshooting

### "Table already exists" error
```bash
# Check if table exists
sqlite3 adaptiv_health.db ".schema nutrition_entries"
# If exists, migration already run - skip this step
```

### "401 Unauthorized" error
```bash
# Token expired - login again
curl -X POST http://localhost:8080/api/v1/login \
  -F "username=test@example.com" \
  -F "password=password123"
```

### "422 Validation Error"
```json
// Check request body format:
{
  "meal_type": "breakfast",  // Must be: breakfast/lunch/dinner/snack/other
  "calories": 350            // Must be 0-10000
}
```

### "404 Not Found" on delete
```
// Entry doesn't exist or belongs to another user
// Use GET /api/v1/nutrition/recent to find valid entry_id
```

### Import errors in tests
```bash
# Install requirements
pip install -r requirements.txt
```

---

## 📞 Support

**Questions?** See:
- `ARCHITECT_CHECKLIST.md` - Task #1 completion details
- `docs/NUTRITION_API.md` - Complete API reference
- `docs/NUTRITION_IMPLEMENTATION_SUMMARY.md` - Implementation details

**Backend mode active:** Adaptiv Backend Engineer  
**Scope:** `app/`, `migrations/`, `tests/`, `docs/`
