import kivy
kivy.require('1.10.0')

from kivy.config import Config
Config.set('graphics', 'multisamples', '0')
Config.set('graphics','resizable',0) 

from kivy.core.window import Window
Window.size=500, 700

from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle
from kivy.app import App
from kivy.clock import Clock
from kivy.vector import Vector
from random import randint
from kivy.animation import Animation
from kivy.properties import ListProperty
from functools import partial
from kivy.core.audio import SoundLoader
#生命次数
LIFE=5
#15个石头
STONE=15

#游戏实体基类，主要提供给石头和飞机
class Brain(Widget):  
    def __init__(self, type,  img, velocity, gravity, health, attack, size, direction, pos, status, sound):
        super(Brain, self).__init__()
        self.size=size
        self.type=type
        self.img=img
        self.velocity=velocity
        self.gravity=gravity 
        self.health=health
        self.attack=attack
        self.direction=direction
        self.pos=pos
        self.status=status
        self.sound=SoundLoader.load(sound)
        with self.canvas:
            Rectangle(source=self.img, size=(self.size[0]*1.25, self.size[1]*1.25), pos=self.pos)

#石头或者飞机挂了重置办法   
    def reset(self):
        if self.type=='stone':
            self.pos=randint(0, self.parent.width), self.parent.height+randint(0, self.parent.height)
            self.health=50
        elif self.type=='plane':
            self.health=100
            self.pos=[self.parent.width/2-40, 0]
            anim=Animation(pos=(self.parent.width/2-40, self.parent.height/8), duration=1)
            anim.bind(on_complete=self.alive)
            anim.start(self)

#附属于重置办法            
    def alive(self, anim, obj):
        obj.status='alive'

#尾焰基类
class Tail(Widget):
    def __init__(self):
        super(Tail, self).__init__()
        self.pos=[-100.,-100.]
        self.size=[28,28]
        with self.canvas:
            self.rect1=Rectangle(source='tail.png', size=[28, 28], pos=self.pos)
        self.bind(pos=self.sync)
        
    def sync(self, instance, value):
        instance.canvas.children[1].pos=value

#子弹基类        
class Bullet(Widget):
    def __init__(self):
        super(Bullet, self).__init__()
        self.pos=[-10.,-10.]
        self.size=[7, 15]
        self.attack=10
        with self.canvas:
            Rectangle(source='shoot.png', size=self.size, pos=self.pos)
        self.bind(pos=self.sync)
        
    def shoot(self):
        self.pos=Vector(self.parent.plane.pos)+Vector(self.parent.plane.width/2+3, self.parent.plane.height/2+10)
        self.anim=Animation(pos=[self.pos[0], self.parent.height-20], duration=(self.parent.height-self.pos[1])/500)
        if self.parent is not None:
            self.anim.bind(on_complete=self.resetB)
        self.anim.start(self)
        
    def resetB(self, anim, obj):
        if self.parent is not None:
            self.parent.bullets.remove(obj)
            self.parent.remove_widget(obj)
        obj=None
    
    def sync(self, instance, value):
        instance.canvas.children[1].pos=value

#石头
class Stone(Brain):
    #日常思考要做的事
    def thinking(self, dt):
        self.pos=self.x, self.y-dt*self.velocity
        if self.y<0:
            self.reset()
        if self.health<=0:
            self.sound.play()
            self.parent.explosion(Vector(self.pos)+Vector(-self.width, -self.height))
            self.parent.score=self.parent.score+100
            self.parent.scoreLabel.text='score: '+str(self.parent.score)
            self.reset()

    #检测子弹攻击
    def collide(self, instance):
        self.health=self.health-instance.attack
        if instance is not None:
            self.parent.bullets.remove(instance)
            self.parent.remove_widget(instance)
            del instance

#飞机            
class Plane(Brain):
    #加尾焰
    def addTail(self):
        self.t=0
        for i in range(2):
            fire=Tail()
            fire.pos=Vector(self.pos)+Vector(self.width/2-7, self.height/2-40)
            self.add_widget(fire)

    #日常动作，这里只有尾焰处理
    def thinking(self, dt):
        self.children[0].pos=Vector(self.pos)+Vector(self.width/2-7, self.height/2-randint(30, 40))
        self.children[1].pos=Vector(self.pos)+Vector(self.width/2-7, self.height/2-randint(30, 40))
    
    #检查是否被石头撞了
    def collide(self, instance):
        self.parent.explosion(Vector(self.pos)+Vector(-self.width, -self.height))
        self.sound.play()
        self.status='die'
        instance.reset()
        self.reset()
        self.parent.life=self.parent.life-1
        self.parent.lifeLabel.text='Life: '+str(self.parent.life)
        self.children[0].pos=[-100, -100]
        self.children[1].pos=[-100, -100]
    
    #按键盘移动
    def move(self, key, dt):
        if key==97:
            self.pos=Vector(self.pos)+Vector(-dt*self.velocity, 0)
        elif key==100:
            self.pos=Vector(self.pos)+Vector(dt*self.velocity, 0)
        elif key==115:
            self.pos=Vector(self.pos)+Vector(0, -self.velocity*dt)
        elif key==119:
            self.pos=Vector(self.pos)+Vector(0, self.velocity*dt)
        if self.pos[0]<0:
            self.pos[0]=0
        if self.pos[0]>self.parent.width-self.size[0]:
            self.pos[0]=self.parent.width-self.size[0]
        if self.pos[1]<0:
            self.pos[1]=0
        if self.pos[1]>self.parent.height-self.size[1]:
            self.pos[1]=self.parent.height-self.size[1]

#游戏主逻辑
class PlaneGame(Widget):
    pos=ListProperty(None)
    def __init__(self):
        super(PlaneGame, self).__init__()
        #绑定键盘
        self.keyboard = Window.request_keyboard(self.keyboard_closed, self, 'text')
        self.keyboard.bind(on_key_down=self.on_keyboard_down, on_key_up=self.on_keyboard_up)
        self.size=Window.size
        
        #各种初始
        self.shoot=False
        self.move=0
        self.entities=[]
        self.bullets=[]
        with self.canvas:
            Rectangle(source='bk.png', size=self.size)
            self.rect=Rectangle(source='explosion1.png', size=[150, 150], pos=[-1000, -1000])
        
        self.noteLabel=Label(text='A:left,D:right,W:up,S:down,Space:shoot ', font_size='20sp', pos=[200, 20])
        self.add_widget(self.noteLabel)
        
        self.score=0
        self.scoreLabel=Label(text='score: '+str(self.score), font_size='20sp')
        self.scoreLabel.pos=[20, self.height-100]
        self.life=LIFE
        self.lifeLabel=Label(text='Life: '+str(self.life), font_size='20sp')
        self.scoreLabel.pos=[20, self.height-110]
        self.add_widget(self.scoreLabel)
        self.add_widget(self.lifeLabel)
        
        #加飞机
        self.plane=Plane('plane', 'ship.png', 200, 10, 100, 40, (50, 50), 0, [self.width/2-40,self.height/8], 'alive', 'explosion.mp3')
        self.plane.addTail()
        self.plane.bind(pos=self.sync)
        self.add_widget(self.plane)
        self.entities.append(self.plane)
        
        #加石头
        self.stones=[]
        for i in range(STONE):
            stone=Stone('stone', 'sandstone_'+str(randint(1, 4))+'.png', 200, 0, 50, 90, (35, 35), -180, [randint(0, self.width),self.height+randint(0, self.height)], 'alive', 'explosion.mp3')
            self.add_widget(stone)
            self.entities.append(stone)
            self.stones.append(stone)
            stone.bind(pos=self.sync)
        
        #设定任务
        Clock.schedule_interval(self.processing, 1/35)
    
    #任务执行主逻辑
    def processing(self, dt):
        #生命检查
        if self.life<=0:
            self.label=Label(text='Game Over', font_size='20sp', markup=True)
            self.label.pos=self.width/2-self.label.width/2, self.height/2
            
            self.button=Button(text='start', font_size='20sp')
            self.button.size=300, 80
            self.button.pos=self.width/2-self.button.width/2, self.height/2-70
            self.button.bind(on_release=self.restart)
            
            self.add_widget(self.label)
            self.add_widget(self.button)
            
            Clock.unschedule(self.processing)
        #攻击
        if self.shoot:
            self.bullet=Bullet()
            self.bullets.append(self.bullet)
            self.add_widget(self.bullet)
            self.bullet.shoot()
            
        #移动
        if self.move>0:
            self.plane.move(self.move, dt)
        
        #碰撞检测
        for each in self.entities:
            if each.status=='alive':
                each.thinking(dt)
                if each.type=='stone' and self.plane.collide_widget(each) and self.plane.status=='alive':
                    self.plane.collide(each)
                if each.type=='stone':
                    for b in self.bullets:
                        if each.collide_widget(b):
                            each.collide(b)
    
    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[0]==32:
            self.shoot=True
        elif keycode[0]==97 or keycode[0]==119 or keycode[0]==100 or keycode[0]==115:
            self.move=keycode[0]

    def on_keyboard_up(self, keyboard, keycode):
        if keycode[0]==32:
            self.shoot=False
        elif keycode[0]==97 or keycode[0]==119 or keycode[0]==100 or keycode[0]==115:
            self.move=0

    def keyboard_closed(self):
        self.keyboard.unbind(on_key_down=self.on_keyboard_down)
        self.keyboard = None
            
    def sync(self, instance, value):
        instance.canvas.children[1].pos=value
    
    def explosion(self, pos):
        def u(rect, source, *args):
            rect.source=source
        def rem(rect, *args):
            self.rect.pos=[-1000, -1000]
        self.rect.pos=pos
        Clock.schedule_once(partial(u, self.rect,'explosion1.png' ), 0.1)
        Clock.schedule_once(partial(u, self.rect,'explosion2.png' ), 0.15)
        Clock.schedule_once(partial(u, self.rect,'explosion3.png' ), 0.2)
        Clock.schedule_once(partial(u, self.rect,'explosion4.png' ), 0.25)
        Clock.schedule_once(partial(u, self.rect,'explosion5.png' ), 0.28)
        Clock.schedule_once(partial(rem, self.rect), 0.3)

    def restart(self, k):
        self.life=5
        self.lifeLabel.text='Life: 5'
        self.scoreLabel.text='score: 0'
        self.remove_widget(self.label)
        self.remove_widget(self.button)
        Clock.schedule_interval(self.processing, 1/35)
       
class FlightApp(App):
    def build(self):
        return PlaneGame()

if __name__=='__main__':
    FlightApp().run()
