import layer
import tensorflow as tf



class autoencoder(object):
    
    def __init__(self,units,act):
        
        assert len(units)-1==len(act),"Number of layers and number of activation functions must be the same (len(units)-1 == len(act_func))"
        self.layers = []
        self.units = units
        self.act_func = act
        self.enc_length = len(self.units)-1
        self.dec_enc_length = self.enc_length*2
        self.is_sym = False
        self.initialized = False
        self.session = None
        self.full_connected = False
        
    def __enter__(self):
        return self
    
    def __exit__(self,exc_type, exc_value, traceback):
        pass
    
    def generate_encoder(self):
         for i in range(self.enc_length):
            self.layers.append(layer.layer([self.units[i],self.units[i+1]],activation=self.act_func[i],mean=0.0,std=2.0))
        

        
    def generate_decoder(self,symmetric=True,act=None):
        
        decoder = []
        if(symmetric):
            self.is_sym=True
            for i in reversed(range(self.enc_length)):
                if (act is None):
                    temp_l = layer.layer([self.units[i+1],self.units[i]],activation=self.act_func[i])
                    self.act_func.append(self.act_func[i])
                else:
                   temp_l = layer.layer([self.units[i+1],self.units[i]],activation=act[i])
                   self.act_func.append(act[i])
                if(i==0):
                    temp_l.W = tf.transpose(self.layers[i].W)
                else:
                    temp_l.W = tf.transpose(self.layers[i].W)
                    temp_l.b = self.layers[i-1].b
               
                decoder.append(temp_l)
        else: #####NON SERVE AD UNA CEPPA DI NIENTE!!
            for i in reversed(range(self.enc_length)):
                if (act is None):
                    temp_l = layer.layer([self.units[i+1],self.units[i]],activation=self.act_func[i])
                    self.act_func.append(self.act_func[i])
                else:
                   temp_l = layer.layer([self.units[i+1],self.units[i]],activation=act[i])
                   self.act_func.append(act[i])
                if(i==0):
                    temp_l.assign_W(self.layers[i].W,T=True)
                else:
                    temp_l.assign(self.layers[i].W,self.layers[i-1].b,T=True)
               
                decoder.append(temp_l)
        
        self.layers.extend(decoder)
        self.full_connected = True
    
     
    def enc_output(self,x,lev=None):
        assert len(self.layers)!=0, 'Before training you must generate encoder and decoder'

        if lev is None:
            lev = 0
        if(lev==self.enc_length-1):
            return self.layers[lev].output(x)
        else:
            return self.enc_output(self.layers[lev].output(x),lev+1)
            
        
    def output(self,x,lev=None):
        assert len(self.layers)!=0, 'Before training you must generate encoder and decoder'
        if lev is None:
            lev = 0
        if(lev==self.dec_enc_length-1):
            return self.layers[lev].output(x)
        else:
            return self.output(self.layers[lev].output(x),lev+1)   
        

   
           
          
            
    def load_model(self,name,session=None,saver=None):
            if(saver is None):
                saver = tf.train.Saver()
            if(session is None):
                init = tf.initialize_all_variables()
                session = tf.Session()
                session.run(init) 
            saver.restore(session, name)
        
   
    
  
    def init_network(self,list_var=None):
       
        if(list_var is None):
            init = tf.initialize_all_variables()
        else:
            init = tf.initialize_variables(list_var)
        
    
        sess = tf.Session()
    
        sess.run(init)
        
        self.initialized=True
        self.session = sess
        return sess
    
    
    def pre_train(self,data,n_iters=100,session=None):
        assert self.full_connected,"Pretraining can be done only with a full autoencoder (encoder+decoder). Use generate_decoder() first."
        
        
        old = None
        params = []
        for i in range(self.enc_length):
            with autoencoder(self.units[i:i+2],[self.act_func[i]]) as temp:

                temp.generate_encoder() 
                temp.generate_decoder()

                temp_session = temp.init_network()
                
                print 'Pretraining layer %d: '%(i+1),'...'
                prt = 'pre_trained_layer'+str(i+1)+'.ckpt'
                if(i==0):
                    ic,bc = temp.train(data,batch=None,model_name=prt,display=False,verbose=False,noise=False,n_iters=n_iters) 
                    old = temp_session.run(temp.enc_output(data))
                    params.extend([temp_session.run(temp.layers[0].W),temp_session.run(temp.layers[0].b),temp_session.run(temp.layers[1].W),temp_session.run(temp.layers[1].b)])
                else:
                    ic,bc = temp.train(old,batch=None,model_name=prt,display=False,verbose=False,noise=False,n_iters=n_iters)
                    params.extend([temp_session.run(temp.layers[0].W),temp_session.run(temp.layers[0].b),temp_session.run(temp.layers[1].W),temp_session.run(temp.layers[1].b)])
                    old = temp_session.run(temp.enc_output(old))
                print '...finshed initial cost: ',ic,' final: ',bc
        
        units = self.units
        rev_units = units[::-1]

        for i in range(self.enc_length):
            W_trained = tf.Variable(tf.add(tf.zeros(units[i:i+2]),params[i*4]))
            b_trained = tf.Variable(tf.add(tf.zeros([units[i+1]]),params[(i*4)+1]))
            if(i==0):
                W_trained_T = tf.Variable(tf.add(tf.zeros(rev_units[-2:]),params[(i*4)+2]))
                b_trained_T = tf.Variable(tf.add(tf.zeros([rev_units[-1]]),params[(i*4)+3]))
            else:
                W_trained_T = tf.Variable(tf.add(tf.zeros(rev_units[-2-i:-i]),params[(i*4)+2]))
                b_trained_T = tf.Variable(tf.add(tf.zeros([rev_units[-i-1]]),params[(i*4)+3]))
                
            self.layers[i].assign(W_trained,b_trained)
   
            self.layers[-1-i].assign(W_trained_T,b_trained_T)
            
        self.session = self.init_network()
        
        return params
    
    def train(self,data,batch,gradient='gradient',learning_rate=0.1,model_name='./model.ckpt',verbose=True,le=False,tau=1.0,session=None,n_iters=1000,display=False,noise=False,noise_level=1.0):
        
        if(not(batch is None)):
            n_batch = len(batch)
        
        if((session is None) and (self.session is None)):
            session = self.init_network()
        elif(self.session is None):
            self.session = session
        
        
        if(display):
            import matplotlib.pyplot as plt
            plt.axis([0, 1, 0, 1])
            plt.ion()
            plt.show()
        
    
        best = 20000000
        reg_lambda = 0.015
        
        x = tf.placeholder("float",[None,self.units[0]])
        x_noise = x+tf.truncated_normal([self.units[0]],mean=0.0,stddev=noise_level)
        
        y = self.enc_output(x)
    
        x_hat = self.output(x)
        x_noise_hat = self.output(x_noise)
        #reg_norm = tf.sqrt(tf.reduce_sum(tf.pow(x_hat,2)))
        reg_norm = tf.reduce_mean(tf.sqrt(tf.pow(x_hat,2)))                         
        #reg_norm_noise = tf.sqrt(tf.reduce_sum(tf.pow(x_noise_hat,2)))
        reg_norm_noise = tf.reduce_mean(tf.sqrt(tf.pow(x_noise_hat,2)))  
        #neigh = tf.placeholder("float",[k,self.units[0]])
        
        #rec_weigh = tf.exp(-tf.pow(tf.sqrt(tf.pow(x-neigh,2)),2)/tau)
        #############################
        
        #############################
       
        if(le):
            cost = tf.reduce_mean(tf.sum())
            #dovrebbe essere la somma non la media ma dovrebbe andare uguale
        else:
            #cost = tf.reduce_mean(tf.sqrt(tf.pow(x-x_hat,2)))-reg_lambda*reg_norm  
            cost = tf.reduce_mean((tf.pow(x-x_hat,2)))
        #noise_cost = tf.reduce_mean(tf.sqrt(tf.pow(x-x_noise_hat,2)))-reg_lambda*reg_norm_noise 
        noise_cost = tf.reduce_mean((tf.pow(x-x_noise_hat,2)))
    
        #opt = tf.train.AdamOptimizer()

# Compute the gradients for a list of variables.
        #test = opt.compute_gradients(cost,[self.layers[0].W])
        
        
        if(gradient=='gradient'):
            tr = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost)
        elif(gradient=='adam'):
            tr = tf.train.AdamOptimizer(learning_rate).minimize(cost)
        elif(gradident=='adagrad'):
            tr = tf.train.AdagradOptimizer(learning_rate).minimize(cost)
        elif(gradient=='momentum'):
            tr = tf.train.MomentumOptimizer(learning_rate).minimize(cost)
        elif(gradient=='ftrl'):
            tr = tf.train.FtrlOptimizer(learning_rate).minimize(cost)
        elif(gradient=='rms'):
            tr = tf.train.RMSPropOptimizer(learning_rate).minimize(cost)
        else:
            print "Unknow method ",gradient," .Using Gradient Descent Optimizer"
            tr = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost)
        
        tr_noise = tf.train.GradientDescentOptimizer(learning_rate).minimize(noise_cost)
        
        self.session.run(tf.initialize_all_variables())
        
        #writer = tf.python.training.summary_io.SummaryWriter("/home/ceru/Scrivania/graph_logs", self.session.graph_def)


        #print session.run(self.layers[0].W)
        
        saver = tf.train.Saver()
        
        saver.save(self.session,model_name)
        
        for i in range(n_iters):
        
            if(batch is None):
                self.session.run(tr,feed_dict={x:data})
            else:
                for l in range(n_batch):
                    self.session.run(tr,feed_dict={x:batch[l]})
                    if(noise):
                        self.session.run(tr_noise,feed_dict={x:batch[l]})
                       
            #print self.session.run(test[0],feed_dict={x:data})
            c=self.session.run(cost,feed_dict={x:data})
            if(i==0):
                init_cost = c
            import numpy as np
            if(np.isnan(c)):
                saver.restore(self.session, model_name)
                break
            if(verbose):
                print "cost ",c," at iter ",i+1
            if(c<best):
                if(display):
                    ridotti = self.session.run(y,feed_dict={x:data})
                    ricostruiti = self.session.run(x_hat,feed_dict={x:data})
                    plt.clf()
                    plt.scatter(ridotti[:,0],ridotti[:,1])
                    plt.draw()
                saver.save(self.session,model_name)
                    #self.save_model(session=self.session)
                if(verbose):
                    print "Best model found so far at iter: %d"%(i+1),"with cost %f"%c
                best = c
       
        #if(saving):
            #self.load_model("model.dat",session=self.session)
        saver.restore(self.session,model_name)
        return init_cost,best
        
    def get_hidden(self,data,session=None):
        if((session is None) and (self.session is None)):
            session = self.init_network()
        elif(self.session is None):
            self.session = session
        xh = tf.placeholder("float",[None,self.units[0]])
        
        
        yh = self.enc_output(xh)    
        return session.run(yh,feed_dict={xh:data})
    
    
    
    def get_output(self,data,session=None):
        if((session is None) and (self.session is None)):
            session = self.init_network()
        elif(self.session is None):
            self.session = session
        xo = tf.placeholder("float",[None,self.units[0]])
        
        
        yo = self.output(xo)    
        return session.run(yo,feed_dict={xo:data})


        
        
  
if __name__ == '__main__':

    import math
    from tools.data_manipulation import batch
    import numpy as np
    

    


    data = np.loadtxt("swiss.dat")
    data = (data+abs(np.min(data)))/np.max(data)
    
    data = data.astype("float32")

    n,dim = data.shape
   
    n_batch = 200
 
   
    int_dim  = 2
    
    #units = [data.shape[1],int(math.ceil(data.shape[1]*1.2))+5,int(max(math.ceil(data.shape[1]/4),int_dim+2)+3),
     #        int(max(math.ceil(data.shape[1]/10),int_dim+1)),int_dim]
    
    units = [3,9,5,2]
    #units = [3,2]
    #act = ['softplus']
    act = ['softplus','sigmoid','tanh']
    #act = ['softplus','softplus','softplus','softplus']
    
    test = autoencoder(units,act)
    
    
    test.generate_encoder()
    test.generate_decoder(act)
    
    ts = test.init_network()
    #ba = batch.knn_batch(data,5)
    #ba.extend(batch.knn_batch(data,8))
    #ba.extend(batch.knn_batch(data,15))
    
    ba = batch.rand_batch(data,n_batch)
    #ba = batch.seq_batch(data,n_batch)
    
    #print ts.run(test.layers[0].W)
    
    #test.pre_train(data)
    
    #print ts.run(test.layers[0].W)
    
    
    test.pre_train(data,n_iters=2000)
    
    test.train(data,batch=ba,display=True,n_iters=1000,noise=False,noise_level=0.25)
    
    
    
    
        

         
    



