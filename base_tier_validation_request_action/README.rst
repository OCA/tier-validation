====================================================
Base Tier Validation - Request Validation Actions
====================================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Fserver--ux-lightgray.png?logo=github
    :target: https://github.com/OCA/server-ux/tree/19.0/base_tier_validation_request_action
    :alt: OCA/server-ux

|badge1| |badge2| |badge3|

This module extends the base tier validation system to trigger custom actions
and raise different types of errors when a validation request is submitted.

**Features:**

* **Block validation requests** with ValidationError
* **Display warnings** with UserError
* **Execute server actions** for custom workflows
* Works with existing tier definition rules (``definition_domain``)
* Choose different constraint types per tier definition

**Table of contents**

.. contents::
   :local:

Use Cases
=========

This module is useful in scenarios such as:

* **Block operations**: Prevent validation for orders exceeding budget limits
* **Display warnings**: Alert users about missing required information
* **Notifications**: Send emails/SMS when validation is requested
* **Logging**: Log important events in chatter or external systems
* **Workflows**: Trigger automated checks or data preparation
* **Audit**: Track high-value transactions

Configuration
=============

To configure constraints on tier definitions:

1. Go to Settings > Technical > Tier Validations > Tier Definitions
2. Open or create a Tier Definition
3. Configure the standard ``definition_domain`` field to define when this tier applies
4. Go to the "More Options" tab
5. In the "Validation Constraints" section, configure:
    * **Constraint Type**: Choose the type of action to trigger
    * **Constraint Message**: Error/warning message (for Block and Warning types)
    * **Server Action**: Action to execute (for Server Action type)

Constraint Types
================

**No Constraint (default)**
  No additional action. Standard tier validation behavior.

**Block (ValidationError)**
  Raises a ValidationError and prevents the validation request completely.
  Use this to enforce hard business rules.

**Warning (UserError)**
  Raises a UserError to alert the user.
  More permissive than Block but still prevents the action.

**Execute Server Action**
  Runs a configured server action without blocking the validation.
  Use this for notifications, logging, or automated workflows.

Usage
=====

**Example 1: Block High Amount Orders**

Prevent validation requests for purchase orders over 50,000:

* Model: Purchase Order
* Apply On: ``[('amount_total', '>', 50000)]``
* Constraint Type: Block (ValidationError)
* Constraint Message: "Purchase orders over 50,000 require special approval process. Contact CFO."

**Example 2: Warn About Missing Information**

Alert users when payment terms are missing:

* Model: Sale Order
* Apply On: ``[('payment_term_id', '=', False)]``
* Constraint Type: Warning (UserError)
* Constraint Message: "This sale order has no payment terms. Please add payment terms."

**Example 3: Send Notification**

Create a server action that posts a message in chatter:

* Server Action Code::

    record.message_post(
        body="Validation requested. Please review urgently.",
        subject="Validation Request",
        message_type="notification"
    )

* Constraint Type: Execute Server Action
* Server Action: Link the created action

**Example 4: Create Activity**

Create a server action that schedules an activity:

* Server Action Code::

    record.activity_schedule(
        'mail.mail_activity_data_todo',
        summary='Purchase Order Needs Approval',
        note='Please review this high-value purchase order.',
        user_id=env.ref('base.user_admin').id
    )

* Constraint Type: Execute Server Action

**Example 5: Block Invoices Without Tax**

Ensure all customer invoices include tax:

* Model: Invoice
* Apply On: ``[('move_type', 'in', ['out_invoice', 'out_refund']), ('amount_tax', '=', 0)]``
* Constraint Type: Block (ValidationError)
* Constraint Message: "Customer invoices must include tax. Verify tax configuration."

**Example 6: Audit Logging**

Log high-value transactions to external system:

* Server Action Code::

    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("AUDIT: PO %s (Amount: %s) requested by %s",
                 record.name, record.amount_total, env.user.name)
    # Call external API if needed

* Constraint Type: Execute Server Action

Known issues / Roadmap
======================

* Future versions may add more error types (AccessError, etc.)
* Consider adding conditional actions based on user groups
* Add option to combine multiple constraint types

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/server-ux/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Credits
=======

Authors
-------

* ForgeFlow

Contributors
------------

* ForgeFlow <https://www.forgeflow.com>

Maintainers
-----------

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

This module is part of the `OCA/server-ux <https://github.com/OCA/server-ux/tree/19.0/base_tier_validation_request_action>`_ project on GitHub.

You are welcome to contribute. To learn how please visit https://odoo-community.org/page/Contribute.
