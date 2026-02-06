# Changelog

All notable changes to this module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [19.0.1.0.0] - 2026-02-06

### Added
- Initial release of base_tier_validation_request_action module
- Three new fields in tier.definition:
  - `constraint_type`: Select type of action to trigger (none/block/warning/server_action)
  - `constraint_message`: Custom error/warning message
  - `constraint_server_action_id`: Server action to execute
- Four constraint types:
  - **No Constraint**: Default behavior, no additional action
  - **Block (ValidationError)**: Raise ValidationError to prevent validation request
  - **Warning (UserError)**: Raise UserError to alert user
  - **Execute Server Action**: Run custom server action for workflows
- Trigger actions based on existing `definition_domain` rules
- Comprehensive test coverage (8 test cases)
- Demo data with practical examples for all constraint types
- Full documentation (README.rst with examples)

### Features
- Seamless integration with base_tier_validation module
- Uses existing tier definition rules (no separate constraint domain)
- Works with any model that inherits tier.validation
- Triggers actions when tier definition applies and validation is requested
- Supports multiple tier definitions with different constraint types
- Prevents reentrant server action execution for safety
- Clear error messages with tier name included

### Technical Details
- Extends tier.definition model with 3 new fields
- Overrides request_validation() method in tier.validation abstract model
- Uses _get_applicable_tier_definitions_with_constraints() to get matching tiers
- Raises ValidationError or UserError based on constraint_type
- Executes server actions with proper context (active_model, active_id, active_ids)
- ~110 lines of Python code total (very lightweight)
- Order of checking: sequence asc (lowest sequence checked first)

### Use Cases
- Block high-value transactions requiring special approval
- Warn users about missing required information
- Send notifications to reviewers
- Log audit trails to external systems
- Create activities for urgent reviews
- Enforce business rules and data quality
