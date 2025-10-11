import 'package:freezed_annotation/freezed_annotation.dart';

part 'user.freezed.dart';

@freezed
sealed class User with _$User {
  const User._();

  const factory User({
    required String id,
    required String username,
    required String email,
    String? name,
    String? profileImage,
    required String role,
    @Default(true) bool isActive,
  }) = _User;

  factory User.fromJson(Map<String, dynamic> json) {
    // Handle different field names from OpenWebUI API
    return User(
      id: json['id'] as String? ?? '',
      username: json['username'] as String? ?? json['name'] as String? ?? '',
      email: json['email'] as String? ?? '',
      name: json['name'] as String?,
      profileImage:
          json['profile_image_url'] as String? ??
          json['profileImage'] as String?,
      role: json['role'] as String? ?? 'user',
      isActive: json['is_active'] as bool? ?? json['isActive'] as bool? ?? true,
    );
  }
}
