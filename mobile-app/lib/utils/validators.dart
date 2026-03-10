class Validators {
  static final RegExp _emailRegex = RegExp(r'^[^@]+@[^@]+\.[^@]+');
  static final RegExp _passwordHasLetter = RegExp(r'[A-Za-z]');
  static final RegExp _passwordHasDigit = RegExp(r'\d');
  static final RegExp _phoneRegex = RegExp(r'^[0-9+\-]+$');

  static String? email(String? value) {
    final trimmed = value?.trim() ?? '';
    if (trimmed.isEmpty) {
      return 'Email is required';
    }
    if (!_emailRegex.hasMatch(trimmed)) {
      return 'Please enter a valid email';
    }
    return null;
  }

  static String? password(String? value) {
    final input = value ?? '';
    if (input.isEmpty) {
      return 'Password is required';
    }
    if (input.length < 8) {
      return 'Password must be at least 8 characters';
    }
    if (!_passwordHasLetter.hasMatch(input)) {
      return 'Password must contain at least one letter';
    }
    if (!_passwordHasDigit.hasMatch(input)) {
      return 'Password must contain at least one digit';
    }
    return null;
  }

  static String? required(String? value) {
    if ((value ?? '').trim().isEmpty) {
      return 'This field is required';
    }
    return null;
  }

  static String? name(String? value) {
    final trimmed = value?.trim() ?? '';
    if (trimmed.isEmpty) {
      return 'Full name is required';
    }
    if (trimmed.length > 255) {
      return 'Full name must be 255 characters or fewer';
    }
    return null;
  }

  static String? age(String? value) {
    final trimmed = value?.trim() ?? '';
    if (trimmed.isEmpty) {
      return null;
    }
    final parsed = int.tryParse(trimmed);
    if (parsed == null || parsed < 1 || parsed > 120) {
      return 'Age must be between 1 and 120';
    }
    return null;
  }

  static String? phone(String? value) {
    final trimmed = value?.trim() ?? '';
    if (trimmed.isEmpty) {
      return null;
    }
    if (trimmed.length < 7 || trimmed.length > 20) {
      return 'Phone must be 7 to 20 characters';
    }
    if (!_phoneRegex.hasMatch(trimmed)) {
      return 'Phone can only contain digits, +, or -';
    }
    return null;
  }

  static String? calories(String? value) {
    final trimmed = value?.trim() ?? '';
    if (trimmed.isEmpty) {
      return null;
    }
    final parsed = int.tryParse(trimmed);
    if (parsed == null || parsed < 0 || parsed > 10000) {
      return 'Calories must be between 0 and 10000';
    }
    return null;
  }

  static String? macroGrams(String? value) {
    final trimmed = value?.trim() ?? '';
    if (trimmed.isEmpty) {
      return null;
    }
    final parsed = int.tryParse(trimmed);
    if (parsed == null || parsed < 0 || parsed > 1000) {
      return 'Value must be between 0 and 1000 grams';
    }
    return null;
  }

  static String? confirmPassword(String? value, String password) {
    final input = value ?? '';
    if (input.isEmpty) {
      return 'Please confirm your password';
    }
    if (input != password) {
      return 'Passwords do not match';
    }
    return null;
  }
}
