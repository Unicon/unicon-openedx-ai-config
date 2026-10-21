.. _about-competency-ids:

About Competency IDs
####################

.. tags:: educator, concept

A Competency ID is an identifier that you assign to a competency in a
Competency taxonomy. It is usually the code that the competency has in its
source framework, such as ``HS.N-RN.A.1``. Studio shows the Competency ID next
to the competency's name, so that you can tell which framework entry a
competency matches, even when two competencies have similar names.

Where a Competency ID Comes From
********************************

You assign Competency IDs in the file that you import to create or update a
Competency taxonomy. The ``id`` column of a CSV file, or the ``id`` field of
each tag in a JSON file, holds the Competency ID. The ``value`` column or field
holds the competency's name.

The following example shows a CSV file with two competencies. The second
competency is nested under the first one.

.. code-block:: text

   id,value,parent_id
   HS.N-RN.A,Extend the properties of exponents to rational exponents,
   HS.N-RN.A.1,Explain how the definition of rational exponents follows from integer exponents,HS.N-RN.A

A Competency ID must follow these rules.

* Every row in the import file needs a Competency ID.
* Each Competency ID must be unique within the taxonomy. Studio does not
  distinguish uppercase from lowercase letters when it compares IDs, so
  ``ABC-1`` and ``abc-1`` count as the same ID.
* A Competency ID can be up to 255 characters long and cannot contain a TAB
  character. Spaces at the start or end of the ID are removed.

Who Uses a Competency ID
************************

* **Administrators** assign Competency IDs when they prepare the file for
  importing a Competency taxonomy.
* **Course authors** see Competency IDs on the Competency Management page,
  where the IDs help them pick the right competency.

Where a Competency ID Appears
*****************************

Competency IDs appear only on the Competency Management page. Each one is shown
as a blue badge in the following places.

* In the competency tree, at the right end of each competency's row.
* Next to the **Demonstrate Mastery For** line, after you select a competency.

Screen readers announce each badge as "Competency ID:" followed by the ID. A
competency without a Competency ID shows no badge.

.. Screenshot needed: taxonomies_competency_id_badges.png
   Alt text: A screenshot of the Competency Management page with a competency
   selected, showing Competency ID badges in the competency tree and next to
   the Demonstrate Mastery For line.

The taxonomy editing page does not show Competency IDs.

Changing a Competency ID
************************

You cannot view or edit a Competency ID on the taxonomy editing page. Competency
IDs are set only by importing a file.

When you re-import a taxonomy, Studio uses the Competency ID to match each row
in the new file to an existing competency. If a row's Competency ID matches an
existing competency, Studio updates that competency, for example by renaming
it. For this reason, keep each competency's Competency ID the same from one
import to the next, and change the competency's name instead when you need to.
For more information about how IDs work during import, see
:ref:`tag-ids-for-taxonomy-import`.

A competency that you add on the taxonomy editing page has no Competency ID.
When you export the taxonomy, the export file puts an internal number in the
``id`` column for that competency. To give the competency a real Competency ID,
replace that number in the exported file with your own ID, and then re-import
the file.

.. _competency-ids-rest-api:

Competency IDs in the REST API
******************************

This section is for developers who work with taxonomies through the Studio
REST API. The endpoints below are relative to
``/api/content_tagging/v1/``.

In the API, a Competency ID is the tag's ``external_id`` field, and the taxonomy
type is the taxonomy's ``taxonomy_type`` field.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Endpoint
     - Competency and Competency ID fields
   * - ``POST taxonomies/import/``
     - Creates a taxonomy from an uploaded file. Send ``taxonomy_type`` as
       ``competency`` or ``tags`` in the form data. The default is ``tags``.
       The ``id`` of each row in the file is stored as that tag's
       ``external_id``.
   * - ``GET taxonomies/`` and ``GET taxonomies/{id}/``
     - Each taxonomy includes ``taxonomy_type``, with the value ``competency``
       or ``tags``.
   * - ``GET taxonomies/{id}/tags/``
     - Each tag includes ``external_id``. The value is ``null`` for a tag that
       has no Competency ID.
   * - ``POST taxonomies/{id}/tags/``
     - Creates a tag. The optional ``external_id`` field sets its Competency ID.
   * - ``PUT taxonomies/{id}/tags/import/``
     - Re-imports a taxonomy from a file. Tags are matched to existing tags by
       ``external_id``. The taxonomy type is not changed.

The API cannot change a tag's ``external_id`` after the tag is created.

.. seealso::

   :ref:`about-competency-taxonomies` (concept)

   :ref:`import-competency-taxonomy` (how-to)

   :ref:`open-competency-management-taxonomy-editing` (how-to)

   :ref:`tag-ids-for-taxonomy-import` (concept)

   :ref:`Update/Re-import a taxonomy` (how-to)


**Maintenance chart**

+--------------+-------------------------------+----------------+--------------------------------+
| Review Date  | Working Group Reviewer        |   Release      |Test situation                  |
+--------------+-------------------------------+----------------+--------------------------------+
|              |                               |                |                                |
+--------------+-------------------------------+----------------+--------------------------------+
