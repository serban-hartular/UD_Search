# The purpose of this module is to collect the various functions I've used to extract or 
# apply annotations to conllu files.
# There are 2 flows:
# To Annotation WebApp:
#   extract from conllu a json dict that the webapp uploads for editing
#   apply the edited json dict back to the conllu
# To Pandas:
#   extract from conllu a dict that can be used to generate a pandas dataframe
#   apply a dict from the pandas dataframe to the conllu
# This should be made to work with ParsedDocs as well

from annotations.annot_sequence import AnnotationSequence, apply_annotations_to_doc, doc_to_annotation_sequence, \
    apply_annot_seq_to_doclist, doclist_to_annot_seq

from annotations.annot_table import doc_to_annotation_table, apply_annotation_table_to_doc, \
    doclist_to_csv_table, apply_annotation_df_to_doclist
