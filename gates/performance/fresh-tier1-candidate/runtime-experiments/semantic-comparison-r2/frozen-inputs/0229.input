"""Adversarial finite tests for complete-response comparison and identity scope."""
import copy
import hashlib
import json
import unittest

from compare_responses import compare, decode, definitions
from make_fixtures import blank_module, balanced, frame, block, identity, transform_ids


def specimen():
    """Build paired valid-shaped synthetic responses with distinct generated IDs."""
    module = blank_module()
    module['predicates'][0]['bodyId'] = balanced(module,2)
    request = frame('comparator',block(module))
    first = {ident:identity(i+100,'server') for i,(_,_,ident) in enumerate(definitions(module))}
    second = {ident:identity(i+500,'server') for i,(_,_,ident) in enumerate(definitions(module))}
    outputs = []
    for assigned,comment in ((first,identity(900,'server')),(second,identity(901,'server'))):
        source = '// literal server:00000000-0000-4000-8000-000000000064\nsig A {}\npred p { some A and some A }\n'
        node = assigned[module['nodes'][0]['id']]
        data = {'mode':'BLOCK_SUPPORTED','source':source,'sourceHash':hashlib.sha256(source.encode()).hexdigest(),
                'module':transform_ids(module,assigned),'diagnostics':[], 'analysisDescriptors':[],
                'idRemapping':assigned,'occurrences':[{'nodeId':node,'role':'reference',
                    'occurrenceId':node+':reference','startUtf16':70,'endUtf16':71}],
                'trivia':[{'commentId':comment,'order':0,'startByte':0,'endByte':51,
                           'anchor':{'kind':'module-leading'}}]}
        outputs.append({'protocol':1,'requestId':request['requestId'],'status':'VALIDATED','data':data})
    return request,*outputs


class ComparatorTests(unittest.TestCase):
    """Require each permitted alpha-renaming and each forbidden mutation separately."""

    def test_generated_identity_bijection(self):
        """Typed definitions and all dependent schema references may rename together."""
        request,left,right = specimen()
        self.assertEqual(compare(left,right,request)['status'],'PASS')

    def test_changed_source_and_recomputed_hash(self):
        """A self-consistent source digest cannot conceal changed source bytes."""
        request,left,right = specimen()
        right['data']['source'] += ' '
        right['data']['sourceHash'] = hashlib.sha256(right['data']['source'].encode()).hexdigest()
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_incorrect_source_digest(self):
        """Both profiles reporting the same wrong hash must still be rejected."""
        request,left,right = specimen()
        left['data']['sourceHash'] = right['data']['sourceHash'] = '0'*64
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_changed_diagnostic(self):
        """Diagnostics remain exact even when they contain UUID-looking strings."""
        request,left,right = specimen()
        right['data']['diagnostics'] = [{'code':'X','message':next(iter(right['data']['idRemapping'].values()))}]
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_changed_trivia_offset(self):
        """Comment byte locations cannot be normalized with generated identities."""
        request,left,right = specimen()
        right['data']['trivia'][0]['startByte'] += 1
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_missing_and_extra_fields(self):
        """Closed result and nested module schemas reject omitted or extra fields."""
        for mutation in ('missing','extra','nested'):
            with self.subTest(mutation=mutation):
                request,left,right = specimen()
                if mutation=='missing': right['data'].pop('trivia')
                elif mutation=='extra': right['data']['unused'] = None
                else:
                    left['data']['module']['unused'] = right['data']['module']['unused'] = None
                with self.assertRaises(AssertionError): compare(left,right,request)

    def test_changed_same_kind_reference_edges(self):
        """Swapping same-kind operand references must not redefine the mapping."""
        request,left,right = specimen()
        root = right['data']['module']['nodes'][-1]
        root['leftId'],root['rightId'] = root['rightId'],root['leftId']
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_alias_collision_and_missing_mapping(self):
        """Every fresh definition needs one distinct corresponding identity."""
        for mutation in ('collision','missing'):
            with self.subTest(mutation=mutation):
                request,left,right = specimen()
                mapping = right['data']['idRemapping']
                a,b = list(mapping)[:2]
                if mutation=='collision': mapping[b] = mapping[a]
                else: mapping.pop(a)
                with self.assertRaises(AssertionError): compare(left,right,request)

    def test_bad_uuid(self):
        """Noncanonical generated ID syntax fails independently of response equality."""
        request,left,right = specimen()
        key = next(iter(right['data']['idRemapping']))
        right['data']['idRemapping'][key] = 'server:not-a-uuid'
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_generated_uuid_version(self):
        """A canonical UUIDv5 is not a fresh random UUIDv4 identity."""
        request,left,right = specimen()
        key = next(iter(right['data']['idRemapping']))
        right['data']['idRemapping'][key] = 'server:00000000-0000-5000-8000-000000000001'
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_unknown_metadata_fields_in_both_profiles(self):
        """Equal extra metadata is still outside the independently closed grammar."""
        for field in ('trivia','occurrences'):
            with self.subTest(field=field):
                request,left,right = specimen()
                left['data'][field][0]['extra'] = right['data'][field][0]['extra'] = 'unchanged'
                with self.assertRaises(AssertionError): compare(left,right,request)

    def test_generated_id_outside_schema(self):
        """Generated identities inserted into diagnostic literals are not translated."""
        request,left,right = specimen()
        left['data']['diagnostics'] = [{'code':'X','message':next(iter(left['data']['idRemapping'].values()))}]
        right['data']['diagnostics'] = [{'code':'X','message':next(iter(right['data']['idRemapping'].values()))}]
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_uuid_looking_source_literal_replacement(self):
        """A UUID-looking source comment remains exact across otherwise valid mapping."""
        request,left,right = specimen()
        right['data']['source'] = right['data']['source'].replace('000000000064','0000000001f4')
        right['data']['sourceHash'] = hashlib.sha256(right['data']['source'].encode()).hexdigest()
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_existing_identity_cannot_rename(self):
        """Trusted inventory identities must stay byte-identical in both responses."""
        request,left,right = specimen()
        key = left['data']['module']['signatures'][0]['id']
        request['ownedIdInventory'][key] = 'signature'
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_all_old_candidate_identities_cannot_disappear(self):
        """Both profiles replacing every owned definition must still fail the input oracle."""
        request,left,right = specimen()
        module = request['candidate']['module']
        mapping = {ident:identity(index+2000,'server') for index,(_,_,ident) in enumerate(definitions(module))}
        request['candidate']['module'] = transform_ids(module,mapping)
        request['ownedIdInventory'] = {mapping[ident]:kind for _,kind,ident in definitions(module)}
        left['data']['idRemapping'] = {}; right['data']['idRemapping'] = {}
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_equal_but_misassociated_remappings(self):
        """A mapping must resolve the declared definition at its typed input position."""
        request,left,right = specimen()
        for result in (left,right):
            mapping = result['data']['idRemapping']
            a,b = list(mapping)[:2]
            mapping[a],mapping[b] = mapping[b],mapping[a]
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_parameters_must_be_arrays(self):
        """An empty object cannot impersonate an empty parameter list in both outputs."""
        request,left,right = specimen()
        for result in (left,right): result['data']['module']['predicates'][0]['parameters'] = {}
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_collection_tag_cannot_move_between_kinds(self):
        """Equal malformed declaration tags do not pass merely by matching each other."""
        request,left,right = specimen()
        for result in (left,right):
            result['data']['module']['signatures'][0] = {'tag':'fact','id':identity(55,'server'),'name':'x','bodyId':identity(56,'server')}
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_json_scalar_types_are_exact(self):
        """Booleans and floating numbers cannot impersonate an integer field."""
        for replacement in (True,1.0,'1'):
            with self.subTest(replacement=replacement):
                request,left,right = specimen()
                right['data']['module']['version'] = replacement
                with self.assertRaises(AssertionError): compare(left,right,request)

    def test_numeric_offsets_do_not_coerce(self):
        """Offset and scope types remain exact outside explicit scalar validators."""
        request,left,right = specimen()
        right['data']['occurrences'][0]['startUtf16'] = 70.0
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_fresh_mapping_cannot_alias_owned_id(self):
        """An identical fresh assignment in both outputs must still avoid old IDs."""
        request,left,_ = specimen()
        old = left['data']['module']['signatures'][0]['id']
        request['ownedIdInventory'][old]='signature'
        with self.assertRaises(AssertionError): compare(left,copy.deepcopy(left),request)

    def test_duplicate_comments(self):
        """Comment identities cannot alias a syntax definition or another comment."""
        request,left,right = specimen()
        for value in (left,right):
            value['data']['trivia'].append(copy.deepcopy(value['data']['trivia'][0]))
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_invalid_responses_compare_every_field(self):
        """Denials compare their complete code and diagnostic payload without mapping."""
        request,left,_ = specimen()
        left.update(status='INVALID',data={'code':'INVALID_DRAFT','diagnostics':[{'code':'X','message':'fixed'}]})
        self.assertEqual(compare(left,copy.deepcopy(left),request)['status'],'PASS')
        right = copy.deepcopy(left)
        right['data']['diagnostics'][0]['message'] = 'changed'
        with self.assertRaises(AssertionError): compare(left,right,request)

    def test_decoder_duplicate_trailing_and_nonfinite(self):
        """Strict decoding rejects ambiguity before fields are compared."""
        for raw in (b'{"x":1,"x":2}\n',b'{}{}\n',b'{"x":NaN}\n',b'{"x":1e9999}\n',b'{\n}\n',b'{}'):
            with self.subTest(raw=raw), self.assertRaises((AssertionError,ValueError)):
                decode(raw)


if __name__ == '__main__':
    unittest.main()
