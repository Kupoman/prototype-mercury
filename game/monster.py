import builtins
import collections
import random

from direct.actor.Actor import Actor
from direct.interval import IntervalGlobal as intervals

from . import gamedb


RANDOM_NAMES = [
    'Aeon Faunagrief',
    'Aeon Valentine',
    'Bedlam Gunner',
    'Belladonna Griefamber',
    'Honor Mourner',
    'Hunter Seraphslayer',
    'Maxim Jester',
    'Maxim Veil',
    'Rage Darkdawn',
    'Raven Grimhunter',
    'Reaper Queenbane',
    'Seraph Ravendragon',
    'Solitaire Knight',
    'Song Darkwarden',
    'Spirit Griffon',
    'Spirit Mistangel',
    'Star Saber',
    'Totem Beastguard',
    'Wolf Steeltotem',
    'Zealot Talon',
]


class MonsterActor:
    _anim_warnings = collections.defaultdict(set)

    def __init__(self, breed, parent_node=None, job=None):
        self.breed = breed

        if job not in self.breed.skins:
            job = 'default'
        skin = self.breed.skins[job]

        if hasattr(builtins, 'base'):
            model = base.loader.load_model('models/{}.bam'.format(skin['bam_file']))
            self._path = Actor(model.find('**/{}'.format(skin['root_node'])))
            if self._path.is_empty():
                print(
                    f"Warning: root node ({skin['root_node']}) not found in "
                    f"bam_file ({skin['bam_file']}) for {breed.id}/{job}"
                )
            self.play_anim('idle', loop=True)
            if parent_node:
                self._path.reparent_to(parent_node)
        else:
            self._path = Actor()

    def __getattr__(self, name):
        return getattr(self._path, name)

    def __estattr__(self, name, value):
        return setattr(self._path, name, value)

    @property
    def as_nodepath(self):
        return self._path

    def _anim_warning(self, anim):
        if isinstance(anim, str):
            baseanim = anim
        else:
            baseanim = anim[-1]
        if baseanim not in self._anim_warnings[self.breed.id]:
            print(f'Warning: {self.breed.name} is missing an animation: {anim}')
            self._anim_warnings[self.breed.id].add(baseanim)

    def play_anim(self, anim, *, loop=False):
        self._path.stop()
        mapped_anim = self.get_anim(anim)
        if mapped_anim is None:
            self._anim_warning(anim)
            return
        if loop:
            self._path.loop(mapped_anim)
        else:
            self._path.play(mapped_anim)

    def get_anim(self, anims):
        if isinstance(anims, str):
            anims = [anims]

        for anim in anims:
            if anim in self._path.get_anim_names():
                return anim
            if anim in self.breed.anim_map:
                return self.breed.anim_map[anim]

        return None

    def actor_interval(self, anim):
        mapped_anim = self.get_anim(anim)
        if mapped_anim is None:
            self._anim_warning(anim)
            return intervals.Sequence()
        return self._path.actor_interval(mapped_anim)


class Monster:
    JP_PER_LEVEL = 100

    BASE_STATS = [
        'hp',
        'physical_attack',
        'magical_attack',
        'accuracy',
        'evasion',
        'defense',
    ]
    def __init__(self, monsterdata):
        self._monsterdata = monsterdata

    def __getattr__(self, name):
        gdb = gamedb.get_instance()
        if name == 'hit_points':
            name = 'hp'
        if name in self.BASE_STATS:
            base_stat = getattr(self.breed, name)
            breed_contrib = getattr(self.breed, f'{name}_affinity') * self.level * 5
            job_contrib = 0
            for jobid, level in ((jobid, self.job_level(jobid)) for jobid in self.jp_totals):
                job = gdb['jobs'][jobid]
                job_contrib += getattr(job, f'{name}_affinity') * level * 5
            return base_stat + breed_contrib + job_contrib
        return getattr(self._monsterdata, name)

    def to_dict(self, skip_extras=False):
        data = self._monsterdata.to_dict()
        if skip_extras:
            return data

        extras = [
            'hit_points',
        ] + self.BASE_STATS
        data.update({
            prop: getattr(self, prop)
            for prop in extras
        })

        return data

    def can_use_job(self, job):
        return set(job.required_tags).issubset(self.tags)

    @classmethod
    def get_random_name(cls):
        return random.choice(RANDOM_NAMES)

    @classmethod
    def make_new(cls, monster_id, name=None, breed_id=None):
        gdb = gamedb.get_instance()

        if name is None:
            name = cls.get_random_name()

        if breed_id is not None:
            breed = gdb['breeds'][breed_id]
        else:
            breed = random.choice([i for i in gdb['breeds'].values() if i.id != 'bobcatshark'])

        monsterdata = gdb.schema_to_datamodel['monsters']({
            'id': monster_id,
            'name': name,
            'breed': breed.id,
            'job': breed.default_job.id,
        })
        monsterdata.link(gdb)

        return cls(monsterdata)

    @classmethod
    def gen_random(cls, monsterid, level):
        mon = cls.make_new(monsterid)

        while mon.level < level:
            job = random.choice(mon.available_jobs)
            mon.add_jp(job, cls.JP_PER_LEVEL)

        mon.job = random.choice(mon.available_jobs)

        return mon

    @property
    def job(self):
        return self._monsterdata.job

    @job.setter
    def job(self, value):
        if not self.can_use_job(value):
            raise RuntimeError(f'tag requirements unsatisfied: {value.required_tags}')
        self._monsterdata.job = value

    def job_level(self, job):
        if not isinstance(job, str):
            job = job.id
        totjp = self.jp_totals.get(job, 0)
        return 1 + totjp // self.JP_PER_LEVEL

    def add_jp(self, job, value):
        if not isinstance(job, str):
            job = job.id
        if job in self.jp_totals:
            self.jp_totals[job] += value
        else:
            self.jp_totals[job] = value

    @property
    def movement(self):
        return self.breed.movement

    @property
    def level(self):
        return 1 + sum((self.job_level(i) - 1 for i in self.jp_totals))

    @property
    def available_jobs(self):
        gdb = gamedb.get_instance()
        return [
            job
            for job in gdb['jobs'].values()
            if self.can_use_job(job)
        ]

    @property
    def tags(self):
        return {
            f'breed_{self.breed.id}',
        } | {
            f'job_{job}_{self.job_level(job)}'
            for job in self.jp_totals
        }

    @property
    def abilities(self):
        return self.job.abilities
