# Developer Documentation

## Architecture

This module extends the base tier validation system by:

1. **Extending tier.definition** - Adds constraint configuration fields
2. **Extending tier.validation** - Adds constraint validation logic before request_validation()

## How It Works

### Flow Diagram

```
User clicks "Request Validation"
    ↓
request_validation() called
    ↓
_check_tier_constraints() executed
    ↓
For each applicable tier definition:
    - Evaluate if tier applies (evaluate_tier)
    - Check constraint type
    - Execute constraint validation
    - Collect error messages
    ↓
If blocking errors found → Raise ValidationError
    ↓
Otherwise → Call super().request_validation()
```

### Constraint Types

#### 1. Required Field
```python
def _check_constraint_required_field(self, tier_definition):
    field = tier_definition.constraint_field_id
    field_value = self[field.name]
    # Check if empty based on field type
    # Return (success, error_message)
```

#### 2. Minimum Amount
```python
def _check_constraint_min_amount(self, tier_definition):
    field = tier_definition.constraint_amount_field_id
    field_value = self[field.name]
    min_amount = tier_definition.constraint_min_amount
    # Compare and return result
```

#### 3. Maximum Amount
Similar to minimum amount but checks upper bound.

#### 4. Domain Constraint
```python
def _check_constraint_domain(self, tier_definition):
    domain = literal_eval(tier_definition.constraint_domain)
    matches = self.filtered_domain(domain)
    # Return success if record matches domain
```

#### 5. Python Code
```python
def _check_constraint_python_code(self, tier_definition):
    eval_context = {
        'rec': self,
        'env': self.env,
        'user': self.env.user,
        # ... more context
    }
    safe_eval(python_code, eval_context, mode='exec')
    result = eval_context.get('result', False)
    # Return result
```

## Extending the Module

### Adding a New Constraint Type

1. **Add selection option to tier_definition.py:**
```python
constraint_type = fields.Selection([
    # ... existing types
    ('my_custom_type', 'My Custom Constraint'),
])
```

2. **Add constraint fields:**
```python
my_custom_field = fields.Char(
    string="Custom Field",
    help="Configuration for my custom constraint"
)
```

3. **Implement validation method in tier_validation.py:**
```python
def _check_constraint_my_custom_type(self, tier_definition):
    """Check custom constraint logic."""
    self.ensure_one()

    # Your validation logic here
    is_valid = True  # or False
    error_msg = ""

    if not is_valid:
        error_msg = tier_definition.constraint_error_message or _(
            "Default error message"
        )
        return False, error_msg

    return True, ""
```

4. **Add to constraint checker:**
```python
def _check_tier_constraints(self):
    # ... existing code
    elif constraint_type == 'my_custom_type':
        success, error_msg = self._check_constraint_my_custom_type(tier_def)
```

5. **Update view (tier_definition_view.xml):**
```xml
<group
    name="my_custom_constraint"
    string="My Custom Constraint"
    invisible="constraint_type != 'my_custom_type'"
>
    <field name="my_custom_field" required="constraint_type == 'my_custom_type'" />
</group>
```

### Adding Custom Actions on Constraint Failure

You can inherit the module to add custom actions:

```python
class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    def request_validation(self):
        # Pre-constraint check action
        self._my_pre_check_action()

        try:
            result = super().request_validation()
        except ValidationError as e:
            # Custom action on constraint failure
            self._log_constraint_failure(str(e))
            raise

        # Post-validation action
        self._my_post_validation_action()

        return result
```

### Adding Model-Specific Constraints

For model-specific constraints:

```python
class SaleOrder(models.Model):
    _inherit = ['sale.order', 'tier.validation']

    def _check_tier_constraints(self):
        """Override to add sale-specific constraints."""
        success, errors = super()._check_tier_constraints()

        # Add custom check
        if self.amount_total > 50000 and not self.payment_term_id:
            errors.append("Payment terms required for orders over 50,000")
            success = False

        return success, errors
```

## Testing

### Running Tests

```bash
# Run all tests for this module
odoo-bin -c config.conf -d test_db -i base_tier_validation_request_action --test-enable --stop-after-init

# Run specific test
odoo-bin -c config.conf -d test_db --test-tags base_tier_validation_request_action
```

### Writing New Tests

```python
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.addons.base_tier_validation.tests.common import CommonTierValidation

@tagged("post_install", "-at_install")
class TestMyConstraint(CommonTierValidation):

    def test_my_constraint_fail(self):
        """Test that my constraint blocks validation request."""
        # Setup
        self.tier_def.write({
            'constraint_type': 'my_custom_type',
            'my_custom_field': 'some_value',
        })

        # Test
        with self.assertRaises(ValidationError) as ctx:
            self.test_record.request_validation()

        self.assertIn("expected error message", str(ctx.exception))

    def test_my_constraint_success(self):
        """Test that my constraint allows validation request."""
        # Setup
        self.tier_def.write({
            'constraint_type': 'my_custom_type',
            'my_custom_field': 'valid_value',
        })

        # Test
        reviews = self.test_record.request_validation()
        self.assertTrue(reviews)
```

## Security Considerations

### Python Code Constraints

Python code constraints use `safe_eval` with restricted context:

- Limited available functions and modules
- No access to system functions
- Cannot import arbitrary modules
- Validated syntax before execution

Available in eval context:
- `rec`: Current record
- `env`: Odoo environment (with ACL)
- `user`: Current user
- `time`, `datetime`: Standard Python modules

**Best Practices:**
- Keep Python code simple
- Avoid complex logic in constraints
- Use domain constraints when possible
- Test thoroughly with different user permissions

### Field Security

Constraint checks respect:
- Field-level security rules
- Record rules
- Model access rights

## Performance Considerations

### Optimization Tips

1. **Use domain constraints** when possible (more efficient than Python)
2. **Minimize Python code complexity** in constraints
3. **Consider caching** for frequently checked values
4. **Use `constraint_block_request=False`** for warnings only
5. **Limit number of constraints** per tier definition

### Benchmarking

```python
import time

def request_validation(self):
    start = time.time()
    result = super().request_validation()
    duration = time.time() - start
    _logger.info(f"Validation took {duration:.3f}s for {self}")
    return result
```

## Common Patterns

### Multi-Currency Amount Checks

```python
constraint_python_code = """
# Check amount in company currency
amount_company = rec.amount_total
if rec.currency_id != rec.company_id.currency_id:
    amount_company = rec.currency_id._convert(
        rec.amount_total,
        rec.company_id.currency_id,
        rec.company_id,
        rec.date or fields.Date.today()
    )
result = amount_company >= 1000.0
"""
```

### Date Range Validation

```python
constraint_python_code = """
from datetime import timedelta
today = fields.Date.today()
max_date = today + timedelta(days=30)
result = rec.date_order and rec.date_order <= max_date
"""
```

### Related Field Checks

```python
constraint_python_code = """
# Ensure partner has required fields
result = (
    rec.partner_id and
    rec.partner_id.vat and
    rec.partner_id.country_id
)
"""
```

## Troubleshooting

### Common Issues

**Issue:** Constraint not triggering
- Check that tier definition applies to the record (domain matches)
- Verify constraint_type is not 'none'
- Check that evaluate_tier() returns True

**Issue:** Python code constraint fails
- Use test_python_expr() to validate syntax
- Check available variables in eval context
- Review error logs for detailed traceback

**Issue:** Performance degradation
- Review Python code complexity
- Check number of active tier definitions
- Consider using domain constraints instead

### Debug Mode

Enable debug logging:

```python
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
```

## API Reference

### Main Methods

#### `_check_tier_constraints()`
Check all tier constraints for a record.

**Returns:** `tuple(success: bool, error_messages: list)`

#### `_get_tier_definitions_for_constraint_check()`
Get applicable tier definitions with constraints.

**Returns:** `tier.definition recordset`

#### `_check_constraint_*()` methods
Individual constraint validation methods.

**Parameters:** `tier_definition: tier.definition record`

**Returns:** `tuple(success: bool, error_message: str)`

## Migration Guide

### From v1.0.0 to v2.0.0 (future)

If breaking changes are introduced in future versions, migration steps will be documented here.

## Contributing

When contributing to this module:

1. Follow OCA guidelines
2. Add tests for new features
3. Update documentation
4. Keep backward compatibility when possible
5. Update CHANGELOG.md

## Support

For issues and questions:
- GitHub Issues: https://github.com/OCA/server-ux/issues
- OCA Community: https://odoo-community.org

## License

AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
