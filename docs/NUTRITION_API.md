# Nutrition API Documentation

## Overview

The Nutrition API provides meal and calorie tracking for AdaptivHealth patients. This feature supports personal health tracking and fitness management.

**Features:**
- Log meals with calories and basic macros (protein, carbs, fat)
- View recent nutrition entries
- Delete entries
- All operations are user-scoped (patients can only access their own data)

**Authentication:** All endpoints require JWT Bearer token authentication.

---

## Data Model

### NutritionEntry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entry_id` | Integer | Auto | Unique entry identifier (PK) |
| `user_id` | Integer | Auto | User who owns this entry (FK → users) |
| `meal_type` | String | ✓ | Type of meal: `breakfast`, `lunch`, `dinner`, `snack`, `other` |
| `description` | String | ✗ | Optional meal description (max 500 chars) |
| `calories` | Integer | ✓ | Total calories (0-10,000) |
| `protein_grams` | Integer | ✗ | Protein in grams (0-500) |
| `carbs_grams` | Integer | ✗ | Carbohydrates in grams (0-1,000) |
| `fat_grams` | Integer | ✗ | Fat in grams (0-500) |
| `timestamp` | DateTime | Auto | When entry was created (timezone-aware) |

---

## Endpoints

### 1. Create Nutrition Entry

**Create a new nutrition entry for the authenticated user.**

```http
POST /api/v1/nutrition
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "meal_type": "breakfast",
  "description": "Oatmeal with berries and almonds",
  "calories": 350,
  "protein_grams": 12,
  "carbs_grams": 45,
  "fat_grams": 14
}
```

**Response (201 Created):**
```json
{
  "entry_id": 123,
  "user_id": 1,
  "meal_type": "breakfast",
  "description": "Oatmeal with berries and almonds",
  "calories": 350,
  "protein_grams": 12,
  "carbs_grams": 45,
  "fat_grams": 14,
  "timestamp": "2026-02-21T10:30:00Z"
}
```

**Minimal Example (only required fields):**
```json
{
  "meal_type": "snack",
  "calories": 150
}
```

**Validation Rules:**
- `meal_type` must be one of: `breakfast`, `lunch`, `dinner`, `snack`, `other` (case-insensitive)
- `calories` must be 0-10,000
- `protein_grams`, `carbs_grams`, `fat_grams` must be 0-500/1000/500 respectively
- `description` cannot be empty string (use `null` instead)

**Error Responses:**
- `400 Bad Request` - Invalid input data or database error
- `401 Unauthorized` - Missing or invalid access token
- `422 Unprocessable Entity` - Validation error (invalid meal_type, negative calories, etc.)

---

### 2. Get Recent Nutrition Entries

**Retrieve recent nutrition entries for the authenticated user, ordered by timestamp descending.**

```http
GET /api/v1/nutrition/recent?limit=5
Authorization: Bearer <access_token>
```

**Query Parameters:**
| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `limit` | Integer | 5 | 1-100 | Maximum number of entries to return |

**Response (200 OK):**
```json
{
  "entries": [
    {
      "entry_id": 125,
      "user_id": 1,
      "meal_type": "dinner",
      "description": "Salmon with vegetables",
      "calories": 580,
      "protein_grams": 42,
      "carbs_grams": 48,
      "fat_grams": 22,
      "timestamp": "2026-02-21T19:00:00Z"
    },
    {
      "entry_id": 124,
      "user_id": 1,
      "meal_type": "lunch",
      "description": "Grilled chicken salad",
      "calories": 420,
      "protein_grams": 35,
      "carbs_grams": 25,
      "fat_grams": 18,
      "timestamp": "2026-02-21T13:00:00Z"
    }
  ],
  "total_count": 47,
  "limit": 5
}
```

**Empty List (no entries):**
```json
{
  "entries": [],
  "total_count": 0,
  "limit": 5
}
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid access token
- `500 Internal Server Error` - Database error

---

### 3. Delete Nutrition Entry

**Delete a specific nutrition entry. Users can only delete their own entries.**

```http
DELETE /api/v1/nutrition/{entry_id}
Authorization: Bearer <access_token>
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entry_id` | Integer | ID of the nutrition entry to delete |

**Response (204 No Content):**
```
(empty body)
```

**Error Responses:**
- `401 Unauthorized` - Missing or invalid access token
- `404 Not Found` - Entry does not exist or does not belong to the authenticated user
- `500 Internal Server Error` - Database error

**Security Note:** Returns `404` instead of `403` when trying to delete another user's entry, preventing information disclosure.

---

## Integration Guide

### Mobile App (Flutter)

**Add to ApiClient (`lib/services/api_client.dart`):**

```dart
// Create nutrition entry
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
    return response.data;
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

// Get recent entries
Future<Map<String, dynamic>> getRecentNutritionEntries({int limit = 5}) async {
  try {
    final response = await _dio.get(
      '/nutrition/recent',
      queryParameters: {'limit': limit},
    );
    return response.data;
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}

// Delete entry
Future<void> deleteNutritionEntry(int entryId) async {
  try {
    await _dio.delete('/nutrition/$entryId');
  } on DioException catch (e) {
    throw _handleDioError(e);
  }
}
```

**Usage in nutrition_screen.dart:**

```dart
// Load recent entries
Future<void> _loadNutritionEntries() async {
  setState(() => _isLoading = true);
  try {
    final data = await widget.apiClient.getRecentNutritionEntries(limit: 10);
    setState(() {
      _entries = List<Map<String, dynamic>>.from(data['entries']);
      _totalCount = data['total_count'];
    });
  } catch (e) {
    setState(() => _errorMessage = e.toString());
  } finally {
    setState(() => _isLoading = false);
  }
}

// Create entry
Future<void> _createEntry() async {
  try {
    await widget.apiClient.createNutritionEntry(
      mealType: _selectedMealType,
      calories: _caloriesController.text.toInt(),
      description: _descriptionController.text,
      proteinGrams: _proteinController.text.isEmpty ? null : _proteinController.text.toInt(),
    );
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Meal logged successfully!')),
    );
    
    _loadNutritionEntries(); // Refresh list
  } catch (e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Error: $e')),
    );
  }
}
```

---

## Database Migration

**SQLite (Development):**
```bash
sqlite3 adaptiv_health.db < migrations/add_nutrition_entries.sql
```

**PostgreSQL (Production):**
```bash
psql -U postgres -d adaptiv_health -f migrations/add_nutrition_entries.sql
```

**Or using Python migration script:**
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
```

---

## Testing

**Run tests:**
```bash
pytest tests/test_nutrition.py -v
```

**Test coverage:**
- ✓ Create entry (success, minimal fields, unauthorized, invalid meal type, negative calories)
- ✓ Get recent entries (empty list, with data, with limit, unauthorized)
- ✓ Delete entry (success, not found, unauthorized)
- ✓ User isolation (users can only access their own entries)

**Manual testing with curl:**

```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:8080/api/v1/login \
  -d "username=test@example.com&password=password123" \
  | jq -r '.access_token')

# 2. Create entry
curl -X POST http://localhost:8080/api/v1/nutrition \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_type": "breakfast",
    "calories": 350,
    "description": "Oatmeal with berries"
  }'

# 3. Get recent entries
curl -X GET "http://localhost:8080/api/v1/nutrition/recent?limit=5" \
  -H "Authorization: Bearer $TOKEN"

# 4. Delete entry
curl -X DELETE "http://localhost:8080/api/v1/nutrition/123" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Design Decisions

### Why Non-Clinical Data?

Nutrition data in this implementation is **not considered Protected Health Information (PHI)** because:
- No medical conditions or allergies tracked
- No prescribed dietary restrictions
- Basic calorie tracking without clinical context
- Data is patient-managed, not clinician-prescribed

If future versions add clinical nutrition plans or medical dietary restrictions, those should be encrypted as PHI.

### Core Feature Set

Current implementation provides:
- ✓ Calories (primary metric for weight management)
- ✓ Protein, Carbs, Fat (essential macros for fitness tracking)

**Possible future enhancements:**
- Micronutrients (vitamins, minerals)
- Meal timing analysis
- Food database integration
- Barcode scanning
- Photo uploads

### Why No Update Endpoint?

Design choice: Nutrition entries are **immutable** after creation.
- Simpler audit trail
- Encourages accuracy at entry time
- Delete + recreate if correction needed

Future enhancement: Add `PATCH /nutrition/{entry_id}` if user feedback indicates need for editing.

---

## Future Enhancements

**Priority 1 (Medium):**
- [ ] Daily/weekly/monthly summaries
- [ ] Calorie target tracking (compare consumed vs. target)
- [ ] Meal timing analysis (time of day patterns)

**Priority 2 (Low):**
- [ ] Food database integration (search for foods)
- [ ] Barcode scanning
- [ ] Photo uploads with meal entries
- [ ] Export to CSV

**Stretch:**
- [ ] AI meal recommendations based on activity and heart health
- [ ] Integration with wearable device step/activity data
- [ ] Nutritionist review features (clinician access with consent)

---

## API Specification Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/nutrition` | POST | ✓ | Create nutrition entry |
| `/api/v1/nutrition/recent` | GET | ✓ | Get recent entries |
| `/api/v1/nutrition/{entry_id}` | DELETE | ✓ | Delete entry |

**Base URL:** `http://localhost:8080` (development) or production domain

**Authentication:** `Authorization: Bearer <access_token>` header

**Content-Type:** `application/json`

**Error Format:**
```json
{
  "detail": "Error message here"
}
```

---

## Checklist

- [x] Model created (`app/models/nutrition.py`)
- [x] Schemas created (`app/schemas/nutrition.py`)
- [x] Router created (`app/api/nutrition.py`)
- [x] Router registered in `app/main.py`
- [x] User relationship added (`user.nutrition_entries`)
- [x] Migration SQL created (`migrations/add_nutrition_entries.sql`)
- [x] Tests created (`tests/test_nutrition.py`)
- [x] Documentation created (`docs/NUTRITION_API.md`)
- [ ] Mobile app integration (nutrition_screen.dart)
- [ ] Database migration run on development environment
- [ ] QA testing with real users

---

For questions or issues, see: `ARCHITECT_CHECKLIST.md` Task #1 or contact the backend team.
