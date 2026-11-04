import unittest
import numpy as np
from allow_retrieval.embedding import compose, Encoder
from allow_retrieval.evaluation import metrics, promotion, evaluate_cached, select_weights, verify_cached_projection, verify_original_manifest

class MLTests(unittest.TestCase):
    def test_layout(self):
        blocks=np.zeros((4,768),dtype=np.float32)
        for i in range(4): blocks[i,i]=1
        vector=compose(blocks)
        self.assertEqual(vector.shape,(3072,))
        for i in range(4): self.assertEqual(vector[i*768+i],.5)
        self.assertAlmostEqual(float(np.linalg.norm(vector)),1)
    def test_invalid(self):
        for x in [np.zeros((4,768)),np.full((4,768),np.nan),np.full((4,768),np.inf),np.ones((4,767))]:
            with self.assertRaises(ValueError): compose(x)
        for scale in (-1000.,1000.):
            adapter=np.zeros((4,768));adapter[0,0]=scale
            with self.assertRaises(ValueError):compose(np.ones((4,768)),adapter)
    def test_real_training(self):
        import tempfile
        from allow_retrieval.training import train
        rng=np.random.default_rng(1)
        pairs=[]
        for i in range(3):
            a=np.ones((4,768),dtype=np.float32)
            a[:,i*10:(i+1)*10] += .6
            pairs.append(dict(record_id=str(i),family=str(i),split='train',certificate_id='self-authored-fixture',left_blocks=a,right_blocks=a+rng.normal(0,.02,size=a.shape)))
        with tempfile.TemporaryDirectory() as d:
            adapter,report=train(pairs,d)
            self.assertTrue(np.any(adapter!=0));self.assertEqual(len(report['history']),20)
            self.assertLess(report['history'][-1]['loss'],report['history'][0]['loss'])
    def test_training_rejects_holdout(self):
        from allow_retrieval.training import train
        with self.assertRaises(ValueError): train([{'split':'test'}],'/unused')

    def test_promotion_rejects_family_leak(self):
        m={'family_macro':{'mrr10':1.0}}
        with self.assertRaises(ValueError): promotion(m,m,[{'family':'a','split':'train'},{'family':'a','split':'test'}],True)

    def test_cached_evaluation_and_grid(self):
        blocks=np.ones((4,768),dtype=np.float32)
        context={'context_key':'k','context_bytes':'[]'}
        content={'context':[],'predicate':['original'],'positives':[['p',i] for i in range(3)],'negatives':[['n',i] for i in range(3)]}
        target=dict(record_id='target',family='f',split='validation',blocks=blocks,content=content,**context)
        query=dict(query_id='query',target_id='target',family='f',split='validation',blocks=blocks,content={**content,'predicate':['variant']},**context)
        report=evaluate_cached([query],[target])
        self.assertEqual(report['family_macro']['mrr10'],1)
        weights,_=select_weights([query],[target])
        self.assertAlmostEqual(weights[0],.45)
        self.assertAlmostEqual(weights[1],.55*.25)

    def test_checked_variant_endpoint_binding(self):
        from allow_retrieval.training import checked_variant_record
        source={'op':'ATOM','sort':'BOOL','atom':'[]','children':[]}
        truth={'op':'TRUE','sort':'BOOL','atom':'','children':[]}
        augmented={'op':'AND','sort':'BOOL','atom':'','children':[source,truth]}
        original={'context':{},'rulesetDigest':'fixture','input':source,'extracted':source}
        cert={**original,'input':augmented}
        variant={'certificateStatus':'CHECKED','certificate':cert,'input':augmented,'extracted':source}
        record={'predicate':{'body':[],'representative':source},'context':[],'positives':[],'negatives':[]}
        result,_=checked_variant_record(record,{'certificate':original},variant)
        self.assertNotEqual(result,record)
        self.assertEqual(result['positives'],record['positives'])
        variant['certificate']={**cert,'context':{'wrong':True}}
        with self.assertRaises(ValueError):checked_variant_record(record,{'certificate':original},variant)

    def test_original_cache_corruption_rejected(self):
        encoder=Encoder()
        record=dict(context=['fixture'],predicate=['original'],positives=[['p',i] for i in range(3)],negatives=[['n',i] for i in range(3)])
        variant={**record,'predicate':['checked-fixture-variant']}
        original,alternate=encoder.encode_blocks(record),encoder.encode_blocks(variant)
        verify_cached_projection(encoder,record,variant,original,alternate)
        corrupt=alternate.copy();corrupt[1,0]+=0.01
        with self.assertRaisesRegex(ValueError,'variant_feature_cache_replay_mismatch'):
            verify_cached_projection(encoder,record,variant,original,corrupt)

    def test_original_manifest_hash_rejected(self):
        import hashlib
        from allow_retrieval.common import canonical
        rows=[{'record_id':'fixture','family':'a','split':'test'}]
        identity=hashlib.sha256(canonical(rows).encode()).hexdigest()
        verify_original_manifest({'id':identity,'rows':rows},identity)
        with self.assertRaisesRegex(ValueError,'original_manifest_changed'):
            verify_original_manifest({'id':identity,'rows':[dict(rows[0],family='b')]},identity)

    def test_macro(self):
        m=metrics([dict(family='a',target_id='x',ranked_target_ids=['x','x']),dict(family='b',target_id='x',ranked_target_ids=['y','x'])])
        self.assertEqual(m['family_macro']['mrr10'],.75)
    def test_pool_order_and_coverage(self):
        class Enc:
            def __init__(self,ids): self.ids=ids
        class Tok:
            def no_truncation(self): pass
            def no_padding(self): pass
            def token_to_id(self,x): return 1
            def encode(self,s,add_special_tokens=False): return Enc([ord(x)%100 for x in s])
        class Input:
            name='input_ids'
        class Session:
            calls=0
            def get_inputs(self): return [Input()]
            def run(self,_,feeds):
                self.calls+=1
                ids=feeds['input_ids'];return [np.repeat((ids+1)[:,:,None],768,axis=2).astype(np.float32)]
        e=Encoder('.',Tok(),Session())
        r=dict(context=['context','x'*1100],predicate=['pred'],positives=[['w',i] for i in range(3)],negatives=[['w',i+3] for i in range(3)])
        a=e.encode_record(r);coverage=e.coverage.copy()
        r['positives'].reverse();np.testing.assert_array_equal(a,e.encode_record(r))
        self.assertTrue(all(x['tokens']==x['covered_tokens'] for x in coverage))
        self.assertGreater(coverage[0]['chunks'],1)
        r['context']=['x'*9000]
        calls=e.session.calls
        with self.assertRaises(ValueError):e.encode_record(r)
        self.assertEqual(e.session.calls,calls)
        r['context']=['short'];r['positives']=[['x'*3000,i] for i in range(3)]
        with self.assertRaises(ValueError):e.encode_record(r)
        self.assertEqual(e.session.calls,calls)

if __name__=='__main__':unittest.main()
