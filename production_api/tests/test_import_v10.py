from main import preview_resume_text

def test_mentions_are_limited_and_not_verified():
    result=preview_resume_text('Tenho projetos com Python e SQL. '*3)
    assert result['skill_mentions']==['python','sql']
    assert result['source']=='user_pasted_text'
    assert 'não comprovam' in result['caveats'][0]

def test_no_substring_false_positive():
    result=preview_resume_text('Meu trabalho foi em uma campanha de javascriptado e sqlista')
    assert result['skill_mentions']==[]
