import io

from game.playerdata import PlayerData


def test_save_load_basic(player):
    ''' Simple round-trip save/load'''

    file_handle = io.StringIO()
    player.save(file_handle)
    file_handle.seek(0)
    _ = PlayerData.load(file_handle)


def test_save_load_no_monster(player):
    '''Save/load when player has no monster'''

    player.monsters = []

    file_handle = io.StringIO()
    player.save(file_handle)
    file_handle.seek(0)
    _ = PlayerData.load(file_handle)

def test_tags(player):
    assert 'in_test' in player.tags
    assert player.can_use_breed(player.monsters[0].breed)

    player.personal_tags.remove('in_test')
    assert not player.can_use_breed(player.monsters[0].breed)
